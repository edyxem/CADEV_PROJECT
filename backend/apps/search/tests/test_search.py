import pytest
from django.core.management import call_command

from apps.accounts.tests.factories import UserFactory
from apps.catalog.tests.factories import TechnologyFactory
from apps.community import services
from apps.community.models import ContentStatus, Post
from apps.community.tests.factories import PostFactory, QuestionFactory
from apps.profiles.models import DeveloperProfile, UserSkill
from apps.projects.models import Project
from apps.projects.tests.factories import make_project
from common.throttling import ScopedWriteThrottle

pytestmark = pytest.mark.django_db


def indexed(**kwargs) -> Post:
    post = PostFactory(**kwargs)
    services.refresh_search_vector(post)
    return post


def ids(response) -> list[str]:
    assert response.status_code == 200, response.json()
    return [item["id"] for item in response.json()["results"]]


class TestPostSearch:
    URL = "/api/v1/search/posts/"

    def test_finds_words_in_title_and_content(self, api_client):
        title_match = indexed(title="Sécuriser une API Django en production")
        content_match = indexed(
            title="Retour d'expérience sur un projet", content="<p>Nous avons durci nos API.</p>"
        )
        indexed(title="Configurer un routeur Cisco")

        found = ids(api_client.get(self.URL, {"q": "API"}))

        assert set(found) == {str(title_match.id), str(content_match.id)}
        assert found[0] == str(title_match.id)

    def test_is_accent_and_stem_insensitive(self, api_client):
        post = indexed(title="Bonnes pratiques de sécurité pour les déploiements")

        assert ids(api_client.get(self.URL, {"q": "securite deploiement"})) == [str(post.id)]

    def test_trigram_tolerates_typos_in_title(self, api_client):
        post = indexed(title="Kubernetes pour les débutants")

        assert ids(api_client.get(self.URL, {"q": "kubernetis"})) == [str(post.id)]

    @pytest.mark.parametrize(
        "status", [ContentStatus.HIDDEN, ContentStatus.DELETED, ContentStatus.DRAFT]
    )
    def test_removed_or_draft_content_is_never_found(self, api_client, status):
        indexed(title="Secret masqué par la modération", status=status, published_at=None)

        assert ids(api_client.get(self.URL, {"q": "masqué"})) == []

    def test_combines_query_with_filters(self, api_client):
        question = QuestionFactory(title="Erreur de migration Django")
        services.refresh_search_vector(question)
        indexed(title="Migration vers Django 5")

        assert ids(api_client.get(self.URL, {"q": "migration", "type": "QUESTION"})) == [
            str(question.id)
        ]

    def test_short_query_returns_recent_posts(self, api_client):
        indexed()

        assert len(ids(api_client.get(self.URL, {"q": "a"}))) == 1

    def test_search_is_rate_limited(self, api_client, monkeypatch):
        monkeypatch.setitem(ScopedWriteThrottle.THROTTLE_RATES, "search", "2/min")

        statuses = [api_client.get(self.URL, {"q": "django"}).status_code for _ in range(3)]

        assert statuses == [200, 200, 429]


class TestUserSearch:
    URL = "/api/v1/search/users/"

    def test_finds_public_profiles_by_name_and_bio(self, api_client):
        amina = UserFactory(username="amina_sec").profile
        amina.bio = "Spécialiste en cybersécurité offensive"
        amina.save()
        UserFactory(username="kwame")

        by_name = api_client.get(self.URL, {"q": "amina"}).json()["results"]
        by_bio = api_client.get(self.URL, {"q": "cybersecurite"}).json()["results"]

        assert [item["username"] for item in by_name] == ["amina_sec"]
        assert [item["username"] for item in by_bio] == ["amina_sec"]

    def test_private_and_disabled_profiles_are_excluded(self, api_client):
        hidden = UserFactory(username="cachee").profile
        hidden.profile_visibility = DeveloperProfile.Visibility.PRIVATE
        hidden.save()
        UserFactory(username="cachee_inactive", is_active=False)

        assert api_client.get(self.URL, {"q": "cachee"}).json()["count"] == 0

    def test_combines_query_with_directory_filters(self, api_client):
        django = TechnologyFactory(name="Django", slug="django")
        with_skill = UserFactory(username="dev_django")
        UserFactory(username="dev_flutter")
        UserSkill.objects.create(user=with_skill, technology=django, level="ADVANCED")

        response = api_client.get(self.URL, {"q": "dev", "technology": "django"})

        assert [item["username"] for item in response.json()["results"]] == ["dev_django"]

    def test_empty_query_lists_public_profiles(self, api_client):
        UserFactory()

        assert api_client.get(self.URL).json()["count"] == 1


class TestGlobalSearch:
    URL = "/api/v1/search/"

    def test_returns_previews_per_type(self, api_client):
        indexed(title="Atelier Django à Abidjan")
        UserFactory(username="django_fan")

        body = api_client.get(self.URL, {"q": "django"}).json()

        assert body["query"] == "django"
        assert len(body["posts"]) == 1
        assert body["users"][0]["username"] == "django_fan"
        assert body["projects"] == []

    def test_short_query_returns_empty_sections(self, api_client):
        body = api_client.get(self.URL, {"q": " x "}).json()

        assert body["posts"] == [] and body["users"] == [] and body["projects"] == []


class TestProjectSearch:
    URL = "/api/v1/search/projects/"

    def test_finds_public_projects_by_name_and_description(self, api_client):
        match = make_project(name="Application de télémédecine rurale", short_description="Santé")
        by_text = make_project(
            name="Outil communautaire", description="<p>Gestion de la télémédecine</p>"
        )
        make_project(name="Jeu éducatif")

        found = [
            item["slug"]
            for item in api_client.get(self.URL, {"q": "telemedecine"}).json()["results"]
        ]

        assert set(found) == {match.slug, by_text.slug}

    def test_private_and_archived_projects_are_excluded(self, api_client):
        make_project(name="Projet secret santé", visibility=Project.Visibility.PRIVATE)
        make_project(name="Projet santé archivé", status=Project.Status.ARCHIVED)

        assert api_client.get(self.URL, {"q": "santé"}).json()["count"] == 0

    def test_typo_tolerance_and_filters(self, api_client):
        project = make_project(name="Cartographie des inondations")
        make_project(name="Cartographie scolaire", accepts_join_requests=False)

        assert [
            p["slug"] for p in api_client.get(self.URL, {"q": "inondasions"}).json()["results"]
        ] == [project.slug]
        recruiting = api_client.get(self.URL, {"q": "cartographie", "recruiting": "true"}).json()
        assert [p["slug"] for p in recruiting["results"]] == [project.slug]
        assert api_client.get(self.URL).json()["count"] == 2

    def test_global_search_includes_projects(self, api_client):
        make_project(name="Plateforme agritech Django")

        assert len(api_client.get("/api/v1/search/", {"q": "agritech"}).json()["projects"]) == 1


def test_rebuild_search_index_command(capsys):
    post = PostFactory(title="Index reconstruit pour Django")
    Post.all_objects.filter(pk=post.pk).update(search_vector=None)

    call_command("rebuild_search_index")

    post.refresh_from_db()
    assert post.search_vector is not None
    assert "1 publication" in capsys.readouterr().out
