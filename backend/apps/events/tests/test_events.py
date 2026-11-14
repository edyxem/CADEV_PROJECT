from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.events.models import Event, EventRegistration
from apps.moderation.services import take_action
from apps.notifications.models import Notification

pytestmark = pytest.mark.django_db

URL = "/api/v1/events/"


def iso(delta: timedelta) -> str:
    return (timezone.now() + delta).isoformat()


def payload(**extra):
    data = {
        "title": "Atelier Django REST Framework",
        "description": "<p>Construisons une API ensemble.</p>",
        "kind": "WORKSHOP",
        "format": "ONLINE",
        "starts_at": iso(timedelta(days=3)),
        "ends_at": iso(timedelta(days=3, hours=2)),
        "online_url": "https://meet.example.org/atelier",
    }
    data.update(extra)
    return data


def make_event(organizer, **extra) -> Event:
    fields = {
        "title": "Meetup",
        "description": "<p>x</p>",
        "starts_at": timezone.now() + timedelta(days=2),
        "ends_at": timezone.now() + timedelta(days=2, hours=2),
        "online_url": "https://meet.example.org/secret",
    }
    fields.update(extra)
    return Event.objects.create(organizer=organizer, **fields)


class TestPublishing:
    def test_member_publishes_event(self, client_for, user):
        response = client_for(user).post(URL, payload(), format="json")

        assert response.status_code == 201, response.json()
        assert response.json()["online_url"] == "https://meet.example.org/atelier"

    @pytest.mark.parametrize(
        "changes",
        [
            {"ends_at": iso(timedelta(days=2))},
            {"starts_at": iso(timedelta(days=-1)), "ends_at": iso(timedelta(hours=1))},
            {"format": "ONSITE"},
            {"online_url": "javascript:alert(1)"},
        ],
    )
    def test_invalid_events(self, client_for, user, changes):
        assert client_for(user).post(URL, payload(**changes), format="json").status_code == 400

    def test_only_organizer_edits_and_cancels(self, client_for, user, other_user):
        event = make_event(user)
        client_for(other_user).post(f"{URL}{event.id}/register/")

        assert (
            client_for(other_user).patch(f"{URL}{event.id}/", {"title": "Piraté"}).status_code
            == 403
        )
        assert (
            client_for(user).patch(f"{URL}{event.id}/", {"title": "Meetup mensuel"}).json()["title"]
            == "Meetup mensuel"
        )
        assert client_for(other_user).post(f"{URL}{event.id}/cancel/").status_code == 403
        assert client_for(user).post(f"{URL}{event.id}/cancel/").json()["status"] == "CANCELLED"
        assert Notification.objects.filter(recipient=other_user, type="EVENT_REMINDER").exists()
        assert client_for(user).post(f"{URL}{event.id}/cancel/").json()["code"] == "event_cancelled"
        assert (
            client_for(user).patch(f"{URL}{event.id}/", {"title": "x"}).json()["code"]
            == "event_cancelled"
        )
        assert client_for(user).delete(f"{URL}{event.id}/").status_code == 404


class TestRegistration:
    def test_online_link_is_reserved_to_registered_members(
        self, client_for, api_client, user, other_user
    ):
        event = make_event(user)
        guest = client_for(other_user)

        assert api_client.get(f"{URL}{event.id}/").json()["online_url"] is None
        assert (
            guest.post(f"{URL}{event.id}/register/").json()["online_url"]
            == "https://meet.example.org/secret"
        )
        assert guest.post(f"{URL}{event.id}/register/").json()["registered_count"] == 1
        assert guest.get(f"{URL}mine/").json()["count"] == 1
        assert guest.delete(f"{URL}{event.id}/register/").json()["is_registered"] is False
        assert guest.post(f"{URL}{event.id}/register/").json()["is_registered"] is True

    def test_capacity_past_and_cancelled(self, client_for, user, other_user):
        full = make_event(user, capacity=1)
        client_for(UserFactory()).post(f"{URL}{full.id}/register/")
        past = make_event(
            user,
            starts_at=timezone.now() - timedelta(days=2),
            ends_at=timezone.now() - timedelta(days=1),
        )
        cancelled = make_event(user, status=Event.Status.CANCELLED)
        client = client_for(other_user)

        assert client.post(f"{URL}{full.id}/register/").json()["code"] == "event_full"
        assert client.post(f"{URL}{past.id}/register/").json()["code"] == "event_past"
        assert client.post(f"{URL}{cancelled.id}/register/").json()["code"] == "event_cancelled"

    def test_registrations_list_is_for_organizer(self, client_for, user, other_user):
        event = make_event(user)
        client_for(other_user).post(f"{URL}{event.id}/register/")

        assert client_for(user).get(f"{URL}{event.id}/registrations/").json()["count"] == 1
        assert client_for(other_user).get(f"{URL}{event.id}/registrations/").status_code == 403


class TestAgendaAndReminders:
    def test_upcoming_and_past(self, api_client, user):
        make_event(user, title="À venir")
        make_event(
            user,
            title="Passé",
            starts_at=timezone.now() - timedelta(days=3),
            ends_at=timezone.now() - timedelta(days=2),
        )

        upcoming = [item["title"] for item in api_client.get(URL).json()["results"]]
        past = [item["title"] for item in api_client.get(URL, {"when": "past"}).json()["results"]]

        assert upcoming == ["À venir"]
        assert past == ["Passé"]
        assert api_client.get(URL, {"when": "all", "kind": "MEETUP"}).json()["count"] == 2

    def test_reminders_are_sent_once(self, user, other_user, capsys):
        soon = make_event(
            user,
            starts_at=timezone.now() + timedelta(hours=5),
            ends_at=timezone.now() + timedelta(hours=6),
        )
        later = make_event(user)
        EventRegistration.objects.create(event=soon, user=other_user)
        EventRegistration.objects.create(event=later, user=other_user)

        call_command("send_event_reminders")
        call_command("send_event_reminders")

        assert Notification.objects.filter(recipient=other_user, type="EVENT_REMINDER").count() == 1
        assert "1 rappel" in capsys.readouterr().out

    def test_moderation_hides_event(self, api_client, user, moderator):
        event = make_event(user)

        take_action(
            moderator=moderator,
            action="HIDE",
            reason="Événement frauduleux.",
            target_type="EVENT",
            target_id=event.pk,
        )

        assert api_client.get(f"{URL}{event.id}/").status_code == 404
