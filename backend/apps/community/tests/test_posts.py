from datetime import timedelta

import pytest
from django.utils import timezone

from apps.catalog.tests.factories import CategoryFactory, TagFactory, TechnologyFactory
from apps.community.models import ContentStatus, Post, PostVote
from apps.community.tests.factories import AnswerFactory, PostFactory, QuestionFactory
from common.throttling import ScopedWriteThrottle

pytestmark = pytest.mark.django_db

URL = "/api/v1/posts/"


def detail(post) -> str:
    return f"{URL}{post.id}/"


@pytest.fixture
def references():
    CategoryFactory(name="Backend et API", slug="backend-et-api")
    TagFactory(name="performance", slug="performance")
    TechnologyFactory(name="Django", slug="django")


def payload(**overrides):
    data = {
        "type": "QUESTION",
        "title": "Pourquoi mes requêtes Django sont-elles lentes ?",
        "content": "<p>J'ai un <strong>N+1</strong> sur ma liste.</p>",
        "environment": "Django 5.2, PostgreSQL 16",
        "category": "backend-et-api",
        "tags": ["performance"],
        "technologies": ["django"],
    }
    data.update(overrides)
    return data


class TestCreatePost:
    def test_member_publishes_a_question(self, client_for, user, references):
        response = client_for(user).post(URL, payload(), format="json")

        assert response.status_code == 201, response.json()
        body = response.json()
        assert body["type"] == "QUESTION"
        assert body["status"] == "PUBLISHED"
        assert body["author"]["username"] == "awa"
        assert body["technologies"][0]["slug"] == "django"
        assert body["vote_count"] == 0 and body["can_edit"] is True
        assert body["published_at"]
        assert Post.all_objects.get().search_vector is not None

    def test_anonymous_cannot_publish(self, api_client, references):
        assert api_client.post(URL, payload(), format="json").status_code == 401

    def test_html_is_sanitized(self, client_for, user, references):
        content = '<p onclick="steal()">ok</p><script>alert(1)</script><a href="javascript:x">l</a>'

        body = client_for(user).post(URL, payload(content=content), format="json").json()

        assert "script" not in body["content"]
        assert "onclick" not in body["content"]
        assert "javascript" not in body["content"]

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("title", "court"),
            ("title", "x" * 151),
            ("content", "<p>   </p>"),
            ("category", "inconnue"),
            ("type", "PROJECT_UPDATE"),
            ("tags", ["a", "b", "c", "d", "e", "f"]),
        ],
    )
    def test_invalid_payloads(self, client_for, user, references, field, value):
        response = client_for(user).post(URL, payload(**{field: value}), format="json")

        assert response.status_code == 400
        assert field in response.json()["errors"]

    def test_announcements_are_reserved_to_moderators(
        self, client_for, user, moderator, references
    ):
        data = payload(type="ANNOUNCEMENT", tags=[], technologies=[])

        assert client_for(user).post(URL, data, format="json").status_code == 403
        assert client_for(moderator).post(URL, data, format="json").status_code == 201

    def test_draft_then_publish(self, client_for, user, other_user, references):
        client = client_for(user)
        draft = client.post(URL, payload(status="DRAFT", content=""), format="json").json()

        assert draft["status"] == "DRAFT" and draft["published_at"] is None
        assert client_for(other_user).get(f"{URL}{draft['id']}/").status_code == 404
        assert client.get(URL).json()["count"] == 0

        published = client.patch(
            f"{URL}{draft['id']}/", {"status": "PUBLISHED", "content": "<p>Prêt</p>"}, format="json"
        )
        assert published.json()["status"] == "PUBLISHED"
        assert client.get(URL).json()["count"] == 1

    def test_published_post_cannot_go_back_to_draft(self, client_for, user):
        post = PostFactory(author=user)

        response = client_for(user).patch(detail(post), {"status": "DRAFT"}, format="json")

        assert response.status_code == 409
        assert response.json()["code"] == "invalid_transition"

    def test_creation_is_rate_limited(self, client_for, user, references, monkeypatch):
        monkeypatch.setitem(ScopedWriteThrottle.THROTTLE_RATES, "content_create", "1/hour")
        client = client_for(user)

        assert client.post(URL, payload(), format="json").status_code == 201
        assert client.post(URL, payload(), format="json").status_code == 429


class TestEditAndDelete:
    def test_author_edits_own_post(self, client_for, user):
        post = PostFactory(author=user)

        response = client_for(user).patch(detail(post), {"title": "Titre corrigé et précis"})

        assert response.status_code == 200
        assert response.json()["title"] == "Titre corrigé et précis"

    @pytest.mark.parametrize("who", ["other_user", "moderator", "admin_user"])
    def test_only_author_can_edit_or_delete(self, request, client_for, user, who):
        post = PostFactory(author=user)
        client = client_for(request.getfixturevalue(who))

        assert client.patch(detail(post), {"title": "Titre détourné par autrui"}).status_code == 403
        assert client.delete(detail(post)).status_code == 403

    def test_anonymous_cannot_edit(self, api_client, user):
        post = PostFactory(author=user)

        assert api_client.patch(detail(post), {"title": "Titre détourné"}).status_code == 401
        assert api_client.delete(detail(post)).status_code == 401

    def test_delete_is_logical_and_keeps_answers(self, client_for, api_client, user):
        question = QuestionFactory(author=user)
        AnswerFactory(question=question)

        assert client_for(user).delete(detail(question)).status_code == 204

        question.refresh_from_db()
        assert question.status == ContentStatus.DELETED
        assert question.answers.count() == 1
        assert api_client.get(detail(question)).status_code == 404
        assert api_client.get(URL).json()["count"] == 0

    def test_hidden_post_is_frozen_for_its_author(self, client_for, user):
        post = PostFactory(author=user, status=ContentStatus.HIDDEN)

        response = client_for(user).patch(detail(post), {"title": "Je contourne la modération"})

        assert response.status_code == 409
        assert response.json()["code"] == "content_removed"


class TestVisibility:
    def test_visitor_reads_published_post(self, api_client):
        post = PostFactory()

        body = api_client.get(detail(post)).json()

        assert body["title"] == post.title
        assert body["has_voted"] is False and body["can_edit"] is False
        assert "email" not in str(body)

    @pytest.mark.parametrize("status", [ContentStatus.HIDDEN, ContentStatus.DELETED])
    def test_removed_content_never_appears_publicly(
        self, api_client, client_for, other_user, status
    ):
        post = PostFactory(status=status)

        assert api_client.get(detail(post)).status_code == 404
        assert client_for(other_user).get(detail(post)).status_code == 404
        assert api_client.get(URL).json()["count"] == 0
        assert api_client.get("/api/v1/questions/").json()["count"] == 0

    def test_author_sees_own_hidden_post_and_moderator_sees_all(self, client_for, user, moderator):
        hidden = PostFactory(author=user, status=ContentStatus.HIDDEN)
        deleted = PostFactory(author=user, status=ContentStatus.DELETED)

        assert client_for(user).get(detail(hidden)).status_code == 200
        assert client_for(user).get(detail(deleted)).status_code == 404
        assert client_for(moderator).get(detail(deleted)).status_code == 200

    def test_mine_lists_drafts_but_not_deleted(self, client_for, user):
        PostFactory(author=user, status=ContentStatus.DRAFT, published_at=None)
        PostFactory(author=user)
        PostFactory(author=user, status=ContentStatus.DELETED)
        PostFactory()

        response = client_for(user).get(f"{URL}mine/")

        assert response.json()["count"] == 2

    def test_mine_requires_authentication(self, api_client):
        assert api_client.get(f"{URL}mine/").status_code == 401


class TestFeed:
    def test_filters(self, api_client):
        django = TechnologyFactory(name="Django", slug="django")
        tag = TagFactory(name="sécurité", slug="securite")
        security = CategoryFactory(name="Cybersécurité", slug="cybersecurite")
        match = PostFactory(category=security, title="Durcir une API Django en production")
        match.technologies.add(django)
        match.tags.add(tag)
        QuestionFactory(title="Configurer un routeur Cisco à distance")

        def ids(**params):
            return [item["id"] for item in api_client.get(URL, params).json()["results"]]

        assert ids(technology="django") == [str(match.id)]
        assert ids(tag="securite") == [str(match.id)]
        assert ids(category="cybersecurite") == [str(match.id)]
        assert ids(type="DISCUSSION") == [str(match.id)]
        assert ids(q="routeur") != [str(match.id)] and len(ids(q="routeur")) == 1
        assert ids(author=match.author.username.upper()) == [str(match.id)]

    def test_orderings(self, api_client, user, other_user):
        old = PostFactory(published_at=timezone.now() - timedelta(days=3))
        popular = PostFactory(published_at=timezone.now() - timedelta(days=2))
        recent = PostFactory()
        unanswered = QuestionFactory(published_at=timezone.now() - timedelta(days=5))
        answered = QuestionFactory(published_at=timezone.now() - timedelta(days=6))
        AnswerFactory(question=answered)
        PostVote.objects.create(user=user, post=popular)
        PostVote.objects.create(user=other_user, post=popular)
        Post.all_objects.filter(pk=old.pk).update(
            last_activity_at=timezone.now() + timedelta(hours=1)
        )

        def first(ordering):
            return api_client.get(URL, {"ordering": ordering}).json()["results"][0]["id"]

        assert first("recent") == str(recent.id)
        assert first("active") == str(old.id)
        assert first("popular") == str(popular.id)
        assert first("unanswered") == str(unanswered.id)
        unanswered_ids = [
            item["id"] for item in api_client.get(URL, {"unanswered": "true"}).json()["results"]
        ]
        assert unanswered_ids == [str(unanswered.id)]

    def test_counts_are_derived_and_pagination_bounded(self, api_client, settings):
        post = PostFactory()
        AnswerFactory.create_batch(2, question=QuestionFactory())
        for _ in range(3):
            PostFactory()

        body = api_client.get(URL, {"page_size": 2, "period": "abc"}).json()

        assert body["count"] == 5 and len(body["results"]) == 2 and body["next"]
        assert api_client.get(URL, {"page_size": 10_000}).status_code == 200
        assert any(item["id"] == str(post.id) for item in api_client.get(URL).json()["results"])

    def test_feed_query_count_is_bounded(self, api_client, django_assert_max_num_queries):
        for _ in range(5):
            PostFactory().technologies.add(TechnologyFactory())

        with django_assert_max_num_queries(6):
            api_client.get(URL)


def test_author_filter_ignores_private_profiles(api_client, user, other_user):
    PostFactory(author=user)
    PostFactory(author=other_user)
    other_user.profile.profile_visibility = "PRIVATE"
    other_user.profile.save()

    assert api_client.get(URL, {"author": "awa"}).json()["count"] == 1
    assert api_client.get(URL, {"author": "kofi"}).json()["count"] == 0
    assert api_client.get("/api/v1/search/posts/", {"author": "kofi"}).json()["count"] == 0
    assert api_client.get(URL).json()["count"] == 2
