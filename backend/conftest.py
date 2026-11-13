"""Fixtures partagées par toute la suite de tests."""

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.accounts.tests.factories import UserFactory


@pytest.fixture(autouse=True)
def _clear_cache():
    """Isole les compteurs de throttling d'un test à l'autre."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def client_for():
    """Fabrique un client d'API authentifié pour l'utilisateur fourni."""

    def _make(user: User | None = None) -> APIClient:
        client = APIClient()
        if user is not None:
            client.force_authenticate(user)
        return client

    return _make


@pytest.fixture
def user(db) -> User:
    return UserFactory(username="awa")


@pytest.fixture
def other_user(db) -> User:
    return UserFactory(username="kofi")


@pytest.fixture
def moderator(db) -> User:
    return UserFactory(username="moussa_mod", role=User.Role.MODERATOR)


@pytest.fixture
def admin_user(db) -> User:
    return UserFactory(username="nadia_admin", role=User.Role.ADMIN)
