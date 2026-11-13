from unittest import mock

import pytest
from django.db import DatabaseError

pytestmark = pytest.mark.django_db


def test_health_reports_database_ok(api_client):
    response = api_client.get("/api/v1/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_returns_503_when_database_is_down(api_client):
    with mock.patch("common.views.connection.cursor", side_effect=DatabaseError):
        response = api_client.get("/api/v1/health/")

    assert response.status_code == 503
    assert response.json()["database"] == "unavailable"


def test_openapi_schema_is_served(api_client):
    response = api_client.get("/api/schema/")

    assert response.status_code == 200
