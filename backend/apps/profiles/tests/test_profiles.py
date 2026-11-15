import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.accounts.tests.factories import UserFactory
from apps.catalog.tests.factories import CategoryFactory, CountryFactory, TechnologyFactory
from apps.profiles.models import DeveloperProfile, SocialLink, UserSkill

pytestmark = pytest.mark.django_db

ME_URL = "/api/v1/profiles/me/"
SKILLS_URL = "/api/v1/profiles/me/skills/"
LINKS_URL = "/api/v1/profiles/me/links/"
AVATAR_URL = "/api/v1/profiles/me/avatar/"


def profile_url(username: str) -> str:
    return f"/api/v1/profiles/{username}/"


def png_upload(name="photo.png", size=(900, 600)) -> SimpleUploadedFile:
    buffer = io.BytesIO()
    Image.new("RGB", size, "orange").save(buffer, "PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


@pytest.fixture
def filled_profile(user):
    profile = user.profile
    profile.city = "Dakar"
    profile.country = CountryFactory(code="SN", name="Sénégal")
    profile.availability_status = DeveloperProfile.Availability.OPEN_TO_COLLABORATION
    profile.save()
    SocialLink.objects.create(user=user, platform="GITHUB", url="https://github.com/awa")
    SocialLink.objects.create(
        user=user, platform="WEBSITE", url="https://awa.example.org", is_public=False
    )
    return profile


class TestProfileCreation:
    def test_profile_is_created_with_the_account(self):
        user = UserFactory(username="sekou")

        assert user.profile.display_name == "sekou"
        assert user.profile.is_public
        assert str(user.profile) == "sekou"

    def test_registration_creates_a_profile_without_photo_or_link(self, api_client):
        api_client.post(
            "/api/v1/auth/register/",
            {"username": "ines", "email": "ines@example.org", "password": "Kilimandjaro-2026"},
        )

        response = api_client.get(profile_url("ines"))

        assert response.status_code == 200
        assert response.json()["avatar"] is None
        assert response.json()["links"] == []


class TestPrivacy:
    def test_public_profile_never_exposes_email_or_private_links(self, api_client, filled_profile):
        body = api_client.get(profile_url("awa")).json()

        assert "email" not in body
        assert "awa@example.org" not in str(body)
        assert [link["url"] for link in body["links"]] == ["https://github.com/awa"]
        assert "profile_visibility" not in body

    def test_hidden_fields_are_nulled_for_others(self, api_client, filled_profile):
        filled_profile.show_city = False
        filled_profile.show_availability = False
        filled_profile.save()

        body = api_client.get(profile_url("awa")).json()

        assert body["city"] is None
        assert body["availability_status"] is None

    def test_owner_sees_hidden_fields_and_private_links(self, client_for, user, filled_profile):
        filled_profile.show_city = False
        filled_profile.save()

        body = client_for(user).get(profile_url("awa")).json()

        assert body["city"] == "Dakar"
        assert len(body["links"]) == 2
        assert body["show_city"] is False

    def test_private_profile_shows_a_minimal_card(self, client_for, other_user, filled_profile):
        filled_profile.profile_visibility = DeveloperProfile.Visibility.PRIVATE
        filled_profile.save()

        body = client_for(other_user).get(profile_url("awa")).json()

        assert body == {
            "username": "awa",
            "display_name": "awa",
            "avatar": None,
            "is_private": True,
        }

    def test_private_profile_is_excluded_from_directory(self, api_client, filled_profile):
        filled_profile.profile_visibility = DeveloperProfile.Visibility.PRIVATE
        filled_profile.save()

        assert api_client.get("/api/v1/profiles/").json()["count"] == 0

    def test_moderator_sees_account_state(self, client_for, moderator, filled_profile):
        body = client_for(moderator).get(profile_url("AWA")).json()

        assert body["email"] == "awa@example.org"
        assert body["is_active"] is True

    def test_disabled_account_profile_is_not_found(self, api_client, user):
        user.is_active = False
        user.save()

        assert api_client.get(profile_url("awa")).status_code == 404


class TestMyProfile:
    def test_anonymous_cannot_edit(self, api_client):
        assert api_client.patch(ME_URL, {"bio": "x"}).status_code == 401

    def test_owner_updates_profile(self, client_for, user):
        CountryFactory(code="CI", name="Côte d'Ivoire")
        CategoryFactory(name="Cybersécurité", slug="cybersecurite")

        response = client_for(user).patch(
            ME_URL,
            {
                "display_name": "Awa D.",
                "bio": "<script>alert(1)</script>Passionnée de <b>Django</b>",
                "country": "ci",
                "domains": ["cybersecurite"],
                "languages": ["fr", "en", "fr"],
                "experience_level": "ADVANCED",
                "availability_status": "LOOKING_FOR_PROJECT",
                "profile_visibility": "PRIVATE",
            },
            format="json",
        )

        assert response.status_code == 200, response.json()
        body = response.json()
        assert body["bio"] == "Passionnée de Django"
        assert body["country"] == "CI"
        assert body["domains"] == ["cybersecurite"]
        assert body["languages"] == ["fr", "en"]
        assert body["profile_visibility"] == "PRIVATE"

    def test_invalid_choices_are_rejected(self, client_for, user):
        response = client_for(user).patch(
            ME_URL, {"languages": ["xx"], "availability_status": "BOSS"}, format="json"
        )

        assert response.status_code == 400
        assert set(response.json()["errors"]) == {"languages", "availability_status"}

    def test_blank_display_name_is_refused(self, client_for, user):
        response = client_for(user).patch(ME_URL, {"display_name": "<i></i>"})

        assert response.status_code == 400

    def test_read_only_fields_cannot_be_forged(self, client_for, user):
        client_for(user).patch(ME_URL, {"username": "pirate", "skills": []}, format="json")

        user.refresh_from_db()
        assert user.username == "awa"


class TestSkills:
    def test_skills_are_self_declared_by_default(self, client_for, user):
        TechnologyFactory(name="Django", slug="django")

        response = client_for(user).put(
            SKILLS_URL,
            [{"technology": "django", "level": "ADVANCED", "years_experience": 4}],
            format="json",
        )

        assert response.status_code == 200
        skill = response.json()[0]
        assert skill["verification_status"] == "SELF_DECLARED"
        assert skill["is_verified"] is False

    def test_evidence_never_marks_a_skill_as_verified(self, client_for, user):
        TechnologyFactory(name="React", slug="react")

        response = client_for(user).put(
            SKILLS_URL,
            [
                {
                    "technology": "react",
                    "level": "EXPERT",
                    "evidence_url": "https://github.com/awa/projet",
                    "verification_status": "PEER_REVIEWED",
                }
            ],
            format="json",
        )

        skill = response.json()[0]
        assert skill["verification_status"] == "EVIDENCE_ADDED"
        assert skill["is_verified"] is False

    def test_put_replaces_and_patch_upserts(self, client_for, user):
        TechnologyFactory(name="Go", slug="go")
        TechnologyFactory(name="Rust", slug="rust")
        client = client_for(user)
        client.put(SKILLS_URL, [{"technology": "go", "level": "BEGINNER"}], format="json")

        client.patch(SKILLS_URL, [{"technology": "rust", "level": "BEGINNER"}], format="json")
        assert user.skills.count() == 2

        client.put(SKILLS_URL, [{"technology": "rust", "level": "INTERMEDIATE"}], format="json")
        assert list(user.skills.values_list("technology__slug", "level")) == [
            ("rust", "INTERMEDIATE")
        ]

    def test_peer_review_is_kept_on_update(self, client_for, user):
        technology = TechnologyFactory(name="Linux", slug="linux")
        UserSkill.objects.create(
            user=user, technology=technology, level="ADVANCED", verification_status="PEER_REVIEWED"
        )

        response = client_for(user).patch(
            SKILLS_URL, [{"technology": "linux", "level": "EXPERT"}], format="json"
        )

        assert response.json()[0]["is_verified"] is True

    def test_duplicates_and_unknown_technologies(self, client_for, user):
        TechnologyFactory(name="PHP", slug="php")
        client = client_for(user)

        duplicate = client.put(
            SKILLS_URL,
            [{"technology": "php", "level": "BEGINNER"}, {"technology": "php", "level": "EXPERT"}],
            format="json",
        )
        unknown = client.put(
            SKILLS_URL, [{"technology": "cobol", "level": "BEGINNER"}], format="json"
        )
        bad_url = client.put(
            SKILLS_URL,
            [{"technology": "php", "level": "BEGINNER", "evidence_url": "ftp://x.org/a"}],
            format="json",
        )

        assert duplicate.status_code == 409
        assert unknown.status_code == 400
        assert bad_url.status_code == 400

    def test_skill_limit(self, client_for, user, monkeypatch):
        monkeypatch.setattr("apps.profiles.services.MAX_SKILLS", 1)
        TechnologyFactory(name="Java", slug="java")
        TechnologyFactory(name="Kotlin", slug="kotlin")

        response = client_for(user).put(
            SKILLS_URL,
            [
                {"technology": "java", "level": "BEGINNER"},
                {"technology": "kotlin", "level": "BEGINNER"},
            ],
            format="json",
        )

        assert response.status_code == 409

    def test_list_my_skills(self, client_for, user):
        assert client_for(user).get(SKILLS_URL).json() == []


class TestSocialLinks:
    def test_owner_manages_links(self, client_for, user):
        client = client_for(user)

        created = client.post(LINKS_URL, {"platform": "GITHUB", "url": "https://github.com/awa"})
        link_id = created.json()["id"]
        updated = client.patch(f"{LINKS_URL}{link_id}/", {"is_public": False})

        assert created.status_code == 201
        assert updated.json()["is_public"] is False
        assert client.get(LINKS_URL).json()[0]["id"] == link_id
        assert client.delete(f"{LINKS_URL}{link_id}/").status_code == 204

    @pytest.mark.parametrize(
        "url", ["javascript:alert(1)", "ftp://files.example.org", "github.com"]
    )
    def test_only_http_links_are_accepted(self, client_for, user, url):
        response = client_for(user).post(LINKS_URL, {"platform": "OTHER", "url": url})

        assert response.status_code == 400

    def test_duplicate_and_limit(self, client_for, user, monkeypatch):
        client = client_for(user)
        client.post(LINKS_URL, {"platform": "GITHUB", "url": "https://github.com/awa"})

        duplicate = client.post(LINKS_URL, {"platform": "GITHUB", "url": "https://github.com/awa"})
        monkeypatch.setattr("apps.profiles.services.MAX_LINKS", 1)
        over_limit = client.post(LINKS_URL, {"platform": "X", "url": "https://x.com/awa"})

        assert duplicate.status_code == 409
        assert over_limit.status_code == 409

    def test_cannot_touch_another_members_link(self, client_for, user, other_user):
        link = SocialLink.objects.create(user=user, platform="GITHUB", url="https://github.com/awa")
        intruder = client_for(other_user)

        assert intruder.patch(f"{LINKS_URL}{link.id}/", {"is_public": False}).status_code == 404
        assert intruder.delete(f"{LINKS_URL}{link.id}/").status_code == 404
        link.refresh_from_db()
        assert link.is_public


class TestAvatar:
    def test_upload_is_reencoded_and_resized(self, client_for, user):
        response = client_for(user).put(AVATAR_URL, {"avatar": png_upload()}, format="multipart")

        assert response.status_code == 200, response.json()
        user.profile.refresh_from_db()
        assert user.profile.avatar.name.endswith(".webp")
        with Image.open(user.profile.avatar.path) as stored:
            assert max(stored.size) == 512

        assert client_for(user).delete(AVATAR_URL).status_code == 204
        user.profile.refresh_from_db()
        assert not user.profile.avatar

    def test_replacing_avatar_deletes_previous_file(self, client_for, user):
        client = client_for(user)
        client.put(AVATAR_URL, {"avatar": png_upload()}, format="multipart")
        user.profile.refresh_from_db()
        first = user.profile.avatar.path

        client.put(AVATAR_URL, {"avatar": png_upload()}, format="multipart")

        import os

        assert not os.path.exists(first)

    def test_disguised_file_is_rejected(self, client_for, user):
        fake = SimpleUploadedFile("photo.png", b"GIF89a<script>", content_type="image/png")

        response = client_for(user).put(AVATAR_URL, {"avatar": fake}, format="multipart")

        assert response.status_code == 400


class TestDirectoryFilters:
    @pytest.fixture
    def directory(self):
        django = TechnologyFactory(name="Django", slug="django")
        senegal = CountryFactory(code="SN", name="Sénégal")
        ghana = CountryFactory(code="GH", name="Ghana")
        security = CategoryFactory(name="Cybersécurité", slug="cybersecurite")

        amina = UserFactory(username="amina").profile
        amina.country, amina.city, amina.languages = senegal, "Dakar", ["fr", "wo"]
        amina.availability_status = DeveloperProfile.Availability.OPEN_TO_COLLABORATION
        amina.experience_level = "EXPERT"
        amina.save()
        amina.domains.add(security)
        UserSkill.objects.create(user=amina.user, technology=django, level="EXPERT")

        kwame = UserFactory(username="kwame").profile
        kwame.country, kwame.city, kwame.languages = ghana, "Accra", ["en"]
        kwame.availability_status = DeveloperProfile.Availability.OPEN_TO_COLLABORATION
        kwame.show_availability = False
        kwame.show_city = False
        kwame.save()

    def usernames(self, api_client, **params):
        response = api_client.get("/api/v1/profiles/", params)
        assert response.status_code == 200
        return sorted(item["username"] for item in response.json()["results"])

    def test_filters(self, api_client, directory):
        assert self.usernames(api_client, technology="django") == ["amina"]
        assert self.usernames(api_client, country="gh") == ["kwame"]
        assert self.usernames(api_client, domain="cybersecurite") == ["amina"]
        assert self.usernames(api_client, language="wo") == ["amina"]
        assert self.usernames(api_client, level="EXPERT") == ["amina"]
        assert self.usernames(api_client, q="kwa") == ["kwame"]
        assert self.usernames(api_client, ordering="username") == ["amina", "kwame"]

    def test_hidden_fields_are_never_used_as_filters(self, api_client, directory):
        assert self.usernames(api_client, availability="OPEN_TO_COLLABORATION") == ["amina"]
        assert self.usernames(api_client, city="accra") == []
        assert self.usernames(api_client, city="DAKAR") == ["amina"]

    def test_directory_query_count_is_bounded(
        self, api_client, directory, django_assert_max_num_queries
    ):
        with django_assert_max_num_queries(8):
            api_client.get("/api/v1/profiles/")


def test_public_profile_exposes_account_id_for_reporting(api_client, user):
    body = api_client.get(profile_url("awa")).json()

    assert body["user_id"] == str(user.id)
    assert "email" not in body
