import pytest
from django.test import Client

from apps.accounts.tests.factories import UserFactory
from apps.community.tests.factories import PostFactory
from common.admin_dashboard import ACTIVITY_DAYS

pytestmark = pytest.mark.django_db

URL = "/admin/afridev-stats/"


@pytest.fixture
def staff_client(admin_user) -> Client:
    # Le statut « staff » découle du rôle (administrateur ou modérateur).
    client = Client()
    client.force_login(admin_user)
    return client


def test_stats_require_staff_login():
    response = Client().get(URL)

    assert response.status_code == 302
    assert "/admin/login/" in response["Location"]


def test_stats_refuse_non_staff_members():
    client = Client()
    client.force_login(UserFactory(username="simple_membre"))

    assert client.get(URL).status_code == 302


def test_stats_return_kpis_and_activity(staff_client):
    PostFactory()
    PostFactory()

    response = staff_client.get(URL)

    assert response.status_code == 200
    assert response["Cache-Control"].startswith("max-age=0")
    data = response.json()
    kpis = {kpi["key"]: kpi["value"] for kpi in data["kpis"]}
    assert set(kpis) == {"members", "posts", "projects", "reports", "opportunities", "events"}
    assert kpis["posts"] == 2
    assert data["activity"]["days"] == ACTIVITY_DAYS
    assert len(data["activity"]["posts"]) == ACTIVITY_DAYS
    assert sum(data["activity"]["posts"]) == 2
    assert len(data["activity"]["members"]) == ACTIVITY_DAYS


def test_stats_reject_other_methods(staff_client):
    assert staff_client.post(URL).status_code == 405


def test_admin_login_uses_afridev_theme():
    response = Client().get("/admin/login/")

    assert response.status_code == 200
    content = response.content.decode()
    assert "afridev_admin/admin.css" in content
    assert "afridev_admin/admin.js" in content


def test_admin_dashboard_renders_for_staff(staff_client):
    response = staff_client.get("/admin/")

    assert response.status_code == 200
    assert "AfriDev" in response.content.decode()


def test_static_storage_tolerates_directory_references():
    # Jazzmin appelle {% static %} sur un dossier : le manifeste ne doit pas être strict.
    from common.storage import StaticStorage

    assert StaticStorage.manifest_strict is False
