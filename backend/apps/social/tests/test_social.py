import pytest
from django.db import IntegrityError

from apps.accounts.tests.factories import UserFactory
from apps.catalog.tests.factories import CategoryFactory, TechnologyFactory
from apps.community.models import ContentStatus
from apps.community.tests.factories import PostFactory
from apps.notifications.models import Notification
from apps.social.models import Follow

pytestmark = pytest.mark.django_db

URL = "/api/v1/follows/"


def follow(client, target_type, target):
    return client.post(URL, {"target_type": target_type, "target": target})


class TestFollows:
    def test_follow_each_target_type(self, client_for, user, other_user):
        TechnologyFactory(name="Django", slug="django")
        CategoryFactory(name="Cybersécurité", slug="cybersecurite")
        client = client_for(user)

        assert follow(client, "USER", "KOFI").status_code == 201
        assert follow(client, "TECHNOLOGY", "django").status_code == 201
        assert follow(client, "CATEGORY", "cybersecurite").status_code == 201

        assert client.get(URL).json()["count"] == 3
        assert (
            client.get(URL, {"target_type": "USER"}).json()["results"][0]["followed_user"][
                "username"
            ]
            == "kofi"
        )
        notification = Notification.objects.get(recipient=other_user)
        assert notification.type == "NEW_FOLLOWER"

    def test_rules(self, client_for, user):
        client = client_for(user)
        UserFactory(username="parti", is_active=False)
        UserFactory(username="sekou")

        assert follow(client, "USER", "awa").json()["code"] == "self_follow"
        assert follow(client, "USER", "inconnu").status_code == 400
        assert follow(client, "USER", "parti").status_code == 400
        assert follow(client, "USER", "sekou").status_code == 201
        assert follow(client, "USER", "sekou").json()["code"] == "already_following"

    def test_limit(self, client_for, user, monkeypatch):
        monkeypatch.setattr("apps.social.services.MAX_FOLLOWS", 1)
        UserFactory(username="un")
        UserFactory(username="deux")
        client = client_for(user)
        follow(client, "USER", "un")

        assert follow(client, "USER", "deux").json()["code"] == "follow_limit"

    def test_database_constraints(self, user, other_user):
        Follow.objects.create(follower=user, target_type="USER", followed_user=other_user)

        with pytest.raises(IntegrityError):
            Follow.objects.create(follower=user, target_type="USER", followed_user=user)

    def test_inconsistent_target_is_rejected_by_database(self, user):
        with pytest.raises(IntegrityError):
            Follow.objects.create(follower=user, target_type="USER", technology=TechnologyFactory())

    def test_unfollow_only_own_subscriptions(self, client_for, user, other_user):
        subscription = Follow.objects.create(
            follower=user, target_type="USER", followed_user=other_user
        )

        assert client_for(other_user).delete(f"{URL}{subscription.id}/").status_code == 404
        assert client_for(user).delete(f"{URL}{subscription.id}/").status_code == 204

    def test_followers_and_stats(self, client_for, api_client, user, other_user):
        Follow.objects.create(follower=other_user, target_type="USER", followed_user=user)

        followers = client_for(user).get(f"{URL}followers/").json()
        stats = api_client.get("/api/v1/profiles/awa/follow-stats/").json()

        assert followers["results"][0]["follower"]["username"] == "kofi"
        assert stats == {"followers": 1, "following": 0}
        assert api_client.get("/api/v1/profiles/inconnu/follow-stats/").status_code == 404

    def test_anonymous_cannot_follow(self, api_client):
        assert follow(api_client, "USER", "awa").status_code == 401
        assert api_client.get("/api/v1/feed/").status_code == 401


class TestPersonalFeed:
    def test_feed_combines_followed_people_technologies_and_categories(
        self, client_for, user, other_user
    ):
        django = TechnologyFactory(name="Django", slug="django")
        security = CategoryFactory(name="Cybersécurité", slug="cybersecurite")
        Follow.objects.create(follower=user, target_type="USER", followed_user=other_user)
        Follow.objects.create(follower=user, target_type="TECHNOLOGY", technology=django)
        Follow.objects.create(follower=user, target_type="CATEGORY", category=security)

        by_author = PostFactory(author=other_user)
        by_technology = PostFactory()
        by_technology.technologies.add(django)
        by_category = PostFactory(category=security)
        PostFactory()
        PostFactory(author=other_user, status=ContentStatus.HIDDEN)
        own = PostFactory(author=user, category=security)

        ids = {item["id"] for item in client_for(user).get("/api/v1/feed/").json()["results"]}

        assert ids == {str(by_author.id), str(by_technology.id), str(by_category.id)}
        assert str(own.id) not in ids

    def test_general_feed_is_unchanged(self, client_for, user, other_user):
        Follow.objects.create(follower=user, target_type="USER", followed_user=other_user)
        PostFactory()

        assert client_for(user).get("/api/v1/posts/").json()["count"] == 1
        assert client_for(user).get("/api/v1/feed/").json()["count"] == 0


class TestBookmarks:
    def test_toggle_idempotent_and_list(self, client_for, user):
        post = PostFactory()
        client = client_for(user)
        url = f"/api/v1/posts/{post.id}/bookmark/"

        assert client.post(url).json() == {"bookmarked": True}
        assert client.post(url, {"active": True}, format="json").json() == {"bookmarked": True}
        assert client.get(f"/api/v1/posts/{post.id}/").json()["has_bookmarked"] is True
        assert client.get("/api/v1/posts/bookmarks/").json()["count"] == 1
        assert client.post(url).json() == {"bookmarked": False}
        assert client.delete(url).json() == {"bookmarked": False}
        assert client.get("/api/v1/posts/bookmarks/").json()["count"] == 0

    def test_removed_posts_leave_bookmarks_list(self, client_for, user):
        post = PostFactory()
        client = client_for(user)
        client.post(f"/api/v1/posts/{post.id}/bookmark/")
        post.status = ContentStatus.HIDDEN
        post.save()

        assert client.get("/api/v1/posts/bookmarks/").json()["count"] == 0

    def test_bookmarks_are_private(self, client_for, api_client, user, other_user):
        post = PostFactory()
        client_for(user).post(f"/api/v1/posts/{post.id}/bookmark/")

        assert client_for(other_user).get("/api/v1/posts/bookmarks/").json()["count"] == 0
        assert api_client.get("/api/v1/posts/bookmarks/").status_code == 401
        assert api_client.post(f"/api/v1/posts/{post.id}/bookmark/").status_code == 401

    def test_cannot_bookmark_a_draft(self, client_for, user):
        draft = PostFactory(author=user, status=ContentStatus.DRAFT, published_at=None)

        assert client_for(user).post(f"/api/v1/posts/{draft.id}/bookmark/").status_code == 409


class TestNotificationPreferences:
    URL = "/api/v1/notifications/preferences/"

    def test_muted_types_are_respected_but_moderation_is_mandatory(
        self, client_for, user, other_user
    ):
        client = client_for(user)

        assert client.get(self.URL).json()["muted_types"] == []
        response = client.patch(
            self.URL, {"muted_types": ["NEW_FOLLOWER", "NEW_FOLLOWER"]}, format="json"
        )
        assert response.json()["muted_types"] == ["NEW_FOLLOWER"]
        assert (
            client.patch(
                self.URL, {"muted_types": ["MODERATION_ACTION"]}, format="json"
            ).status_code
            == 400
        )

        follow(client_for(other_user), "USER", "awa")
        assert not Notification.objects.filter(recipient=user).exists()

        from apps.notifications.services import notify

        notify(user, type="MODERATION_ACTION", title="Décision")
        assert Notification.objects.filter(recipient=user).count() == 1

    def test_invalid_types_and_email_types(self, client_for, user):
        client = client_for(user)

        assert client.patch(self.URL, {"muted_types": ["NOPE"]}, format="json").status_code == 400
        body = client.patch(self.URL, {"email_types": ["TASK_ASSIGNED"]}, format="json").json()
        assert body["email_types"] == ["TASK_ASSIGNED"]
        assert body["mandatory_types"] == ["MODERATION_ACTION"]
