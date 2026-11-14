import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError

from apps.catalog import reference_data
from apps.catalog.models import Category, Country, Tag, Technology
from apps.catalog.normalization import make_slug, normalize_label
from apps.catalog.services import merge_reference_items
from apps.catalog.tests.factories import CategoryFactory, TagFactory, TechnologyFactory
from common.exceptions import BusinessRuleViolation

pytestmark = pytest.mark.django_db


class TestNormalization:
    @pytest.mark.parametrize(
        ("name", "slug"),
        [
            ("C", "c"),
            ("C++", "cpp"),
            ("C#", "csharp"),
            (".NET", "dotnet"),
            ("Node.js", "nodejs"),
            ("  Next.js ", "nextjs"),
            ("Développement web", "developpement-web"),
            ("Frontend et UI/UX", "frontend-et-uiux"),
        ],
    )
    def test_slugs_keep_technologies_distinct(self, name, slug):
        assert make_slug(name) == slug

    def test_label_whitespace_is_collapsed(self):
        assert normalize_label("  Spring   Boot ") == "Spring Boot"

    def test_case_variants_collide_in_database(self):
        Technology.objects.create(name="React")

        with pytest.raises(IntegrityError):
            Technology.objects.create(name="react", slug="react-bis")

    def test_clean_rejects_symbol_only_names(self):
        with pytest.raises(ValidationError):
            Tag(name="!!!").clean()
        with pytest.raises(ValidationError):
            Tag(name="   ").clean()

    def test_country_code_is_uppercased(self):
        country = Country.objects.create(code="ci", name="Côte d'Ivoire")

        assert country.code == "CI"
        assert str(country) == "Côte d'Ivoire"


class TestPublicRead:
    def test_visitor_lists_active_categories_only(self, api_client):
        CategoryFactory(name="Cybersécurité", slug="cybersecurite")
        CategoryFactory(name="Ancienne", slug="ancienne", is_active=False)

        response = api_client.get("/api/v1/categories/")

        assert response.status_code == 200
        assert [item["slug"] for item in response.json()["results"]] == ["cybersecurite"]

    def test_technology_search_and_detail(self, api_client):
        TechnologyFactory(name="Django", slug="django")
        TechnologyFactory(name="Flutter", slug="flutter")

        listing = api_client.get("/api/v1/technologies/", {"search": "djan"})
        detail = api_client.get("/api/v1/technologies/django/")

        assert [item["slug"] for item in listing.json()["results"]] == ["django"]
        assert detail.json()["name"] == "Django"

    def test_inactive_item_is_hidden_from_visitors(self, api_client):
        TagFactory(name="obsolète", slug="obsolete", is_active=False)

        assert api_client.get("/api/v1/tags/obsolete/").status_code == 404

    def test_country_lookup_is_case_insensitive(self, api_client):
        Country.objects.create(code="SN", name="Sénégal")

        assert api_client.get("/api/v1/countries/sn/").json()["code"] == "SN"


class TestAdminWrite:
    URL = "/api/v1/technologies/"

    def test_member_and_moderator_cannot_write(self, client_for, user, moderator, api_client):
        for client in (api_client, client_for(user), client_for(moderator)):
            assert client.post(self.URL, {"name": "Elixir"}).status_code in {401, 403}

    def test_admin_creates_technology_with_normalized_name(self, client_for, admin_user):
        category = CategoryFactory(name="Backend", slug="backend")

        response = client_for(admin_user).post(
            self.URL, {"name": "  Ruby   on Rails ", "category": "backend"}
        )

        assert response.status_code == 201
        technology = Technology.objects.get(slug="ruby-on-rails")
        assert technology.name == "Ruby on Rails"
        assert technology.category == category

    def test_duplicate_with_other_case_is_refused(self, client_for, admin_user):
        TechnologyFactory(name="Docker", slug="docker")

        response = client_for(admin_user).post(self.URL, {"name": "DOCKER"})

        assert response.status_code == 400
        assert "name" in response.json()["errors"]

    def test_rename_updates_slug(self, client_for, admin_user):
        TagFactory(name="perf", slug="perf")

        response = client_for(admin_user).patch("/api/v1/tags/perf/", {"name": "Performance"})

        assert response.json()["slug"] == "performance"

    def test_delete_only_deactivates(self, client_for, admin_user):
        TagFactory(name="spam", slug="spam")
        client = client_for(admin_user)

        assert client.delete("/api/v1/tags/spam/").status_code == 204
        assert Tag.objects.filter(slug="spam", is_active=False).exists()
        assert client.get("/api/v1/tags/spam/").status_code == 200

    def test_invalid_country_code(self, client_for, admin_user):
        response = client_for(admin_user).post(
            "/api/v1/countries/", {"code": "S1", "name": "Inconnu"}
        )

        assert response.status_code == 400
        assert "code" in response.json()["errors"]


class TestMerge:
    def test_cannot_merge_item_into_itself_or_other_type(self):
        tag = TagFactory()
        technology = TechnologyFactory()

        with pytest.raises(BusinessRuleViolation):
            merge_reference_items(tag, tag)
        with pytest.raises(BusinessRuleViolation):
            merge_reference_items(tag, technology)

    def test_merge_deactivates_source(self):
        source, target = TagFactory(name="js", slug="js"), TagFactory(name="javascript")

        merge_reference_items(source, target)

        source.refresh_from_db()
        assert not source.is_active


class TestSeedReference:
    def test_seed_is_idempotent(self):
        call_command("seed_reference")
        call_command("seed_reference")

        assert Category.objects.count() == len(reference_data.CATEGORIES)
        assert Technology.objects.count() == len(reference_data.TECHNOLOGIES)
        assert Tag.objects.count() == len(reference_data.TAGS)
        assert Country.objects.count() == 54

    def test_every_technology_has_its_category(self):
        call_command("seed_reference")

        assert not Technology.objects.filter(category__isnull=True).exists()
        assert Technology.objects.get(slug="cpp").name == "C++"
