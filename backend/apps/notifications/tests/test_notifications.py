import pytest

from apps.accounts.tests.factories import UserFactory
from apps.notifications.models import Notification
from apps.notifications.services import notify

pytestmark = pytest.mark.django_db

URL = "/api/v1/notifications/"
TYPE = Notification.Type.ANSWER_CREATED


def make(recipient, actor=None, **extra):
    return notify(recipient, type=TYPE, title="Nouvelle réponse", actor=actor, **extra)


class TestNotifyService:
    def test_creates_notification_with_target(self, user, other_user):
        notification = make(user, other_user, target=other_user.profile, target_url="/p/1")

        assert notification.target_type == "developerprofile"
        assert notification.target_id == other_user.profile.pk
        assert str(notification) == "awa — Nouvelle réponse"

    def test_no_notification_for_own_action(self, user):
        assert make(user, actor=user) is None
        assert not Notification.objects.exists()

    def test_no_notification_for_missing_or_disabled_recipient(self):
        assert make(None) is None
        assert make(UserFactory(is_active=False)) is None

    def test_long_texts_are_truncated(self, user):
        notification = notify(user, type=TYPE, title="t" * 500, message="m" * 500)

        assert len(notification.title) == 140
        assert len(notification.message) == 300


class TestNotificationApi:
    def test_anonymous_is_rejected(self, api_client):
        assert api_client.get(URL).status_code == 401

    def test_inbox_is_personal_and_paginated(self, client_for, user, other_user):
        make(user, other_user)
        make(other_user, user)

        response = client_for(user).get(URL)

        body = response.json()
        assert body["count"] == 1
        assert body["results"][0]["actor"] == {"username": "kofi"}
        assert "email" not in str(body)

    def test_mark_read_and_filters(self, client_for, user, other_user):
        first, second = make(user, other_user), make(user, other_user)
        client = client_for(user)

        response = client.post(f"{URL}{first.id}/read/")

        assert response.json()["is_read"] is True
        assert client.get(URL, {"is_read": "false"}).json()["count"] == 1
        assert client.get(f"{URL}unread-count/").json() == {"unread": 1}
        assert client.post(f"{URL}read-all/").json() == {"updated": 1}
        second.refresh_from_db()
        assert second.is_read and second.read_at

    def test_cannot_read_someone_elses_notification(self, client_for, user, other_user):
        foreign = make(other_user, user)

        assert client_for(user).post(f"{URL}{foreign.id}/read/").status_code == 404
        foreign.refresh_from_db()
        assert not foreign.is_read
