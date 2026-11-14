"""Règles des événements : capacité, annulation, rappels."""

from datetime import timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone
from rest_framework import exceptions

from apps.accounts.models import User
from apps.notifications.models import Notification
from apps.notifications.services import notify
from common.exceptions import BusinessRuleViolation
from common.sanitization import sanitize_rich_text, to_plain_text

from .models import Event, EventRegistration

REMINDER_WINDOW = timedelta(hours=24)
Registered = EventRegistration.Status.REGISTERED


def event_url(event: Event) -> str:
    return f"/evenements/{event.pk}"


def is_registered(event: Event, user: Any) -> bool:
    return bool(
        user
        and user.is_authenticated
        and EventRegistration.objects.filter(event=event, user=user, status=Registered).exists()
    )


def _validate(data: dict[str, Any], instance: Event | None = None) -> None:
    starts = data.get("starts_at", getattr(instance, "starts_at", None))
    ends = data.get("ends_at", getattr(instance, "ends_at", None))
    if starts and ends and ends <= starts:
        raise exceptions.ValidationError({"ends_at": ["La fin doit suivre le début."]})
    if instance is None and starts and starts < timezone.now():
        raise exceptions.ValidationError(
            {"starts_at": ["L'événement doit avoir lieu dans le futur."]}
        )
    fmt = data.get("format", getattr(instance, "format", Event.Format.ONLINE))
    if fmt in {Event.Format.ONSITE, Event.Format.HYBRID} and not data.get(
        "location", getattr(instance, "location", "")
    ):
        raise exceptions.ValidationError(
            {"location": ["Indiquez le lieu d'un événement en présentiel."]}
        )


@transaction.atomic
def create_event(*, organizer: User, data: dict[str, Any]) -> Event:
    data = dict(data)
    _validate(data)
    community = data.get("community")
    if community is not None:
        from apps.communities.services import ensure_can_publish

        ensure_can_publish(community, organizer)
    technologies = data.pop("technologies", None)
    data["description"] = sanitize_rich_text(data["description"])
    data["title"] = to_plain_text(data["title"])
    event = Event.objects.create(organizer=organizer, **data)
    if technologies:
        event.technologies.set(technologies)
    return event


def update_event(*, event: Event, actor: User, data: dict[str, Any]) -> Event:
    if event.organizer_id != actor.pk:
        raise exceptions.PermissionDenied("Seul l'organisateur modifie l'événement.")
    if event.status == Event.Status.CANCELLED:
        raise BusinessRuleViolation("Cet événement est annulé.", code="event_cancelled")
    data = dict(data)
    _validate(data, event)
    technologies = data.pop("technologies", None)
    if "description" in data:
        data["description"] = sanitize_rich_text(data["description"])
    for field, value in data.items():
        setattr(event, field, value)
    event.save()
    if technologies is not None:
        event.technologies.set(technologies)
    return event


@transaction.atomic
def cancel_event(*, event: Event, actor: User) -> Event:
    if event.organizer_id != actor.pk:
        raise exceptions.PermissionDenied("Seul l'organisateur annule l'événement.")
    if event.status == Event.Status.CANCELLED:
        raise BusinessRuleViolation("Cet événement est déjà annulé.", code="event_cancelled")
    event.status = Event.Status.CANCELLED
    event.save(update_fields=["status", "updated_at"])
    for registration in event.registrations.filter(status=Registered).select_related("user"):
        notify(
            registration.user,
            type=Notification.Type.EVENT_REMINDER,
            title=f"L'événement « {event.title} » est annulé",
            actor=actor,
            target_url=event_url(event),
        )
    return event


@transaction.atomic
def register(*, event: Event, user: User) -> EventRegistration:
    event = Event.objects.select_for_update().get(pk=event.pk)
    if event.status == Event.Status.CANCELLED or event.hidden_by_moderation:
        raise BusinessRuleViolation(
            "Cet événement n'accepte plus d'inscription.", code="event_cancelled"
        )
    if event.ends_at <= timezone.now():
        raise BusinessRuleViolation("Cet événement est terminé.", code="event_past")
    registration = EventRegistration.objects.filter(event=event, user=user).first()
    if registration and registration.status == Registered:
        return registration
    taken = event.registrations.filter(status=Registered).count()
    if event.capacity is not None and taken >= event.capacity:
        raise BusinessRuleViolation("L'événement est complet.", code="event_full")
    if registration is None:
        return EventRegistration.objects.create(event=event, user=user)
    registration.status = Registered
    registration.save(update_fields=["status", "updated_at"])
    return registration


def unregister(*, event: Event, user: User) -> None:
    EventRegistration.objects.filter(event=event, user=user, status=Registered).update(
        status=EventRegistration.Status.CANCELLED, updated_at=timezone.now()
    )


def send_reminders(now: Any = None) -> int:
    """Notifie une fois chaque inscrit d'un événement commençant dans les 24 heures."""
    now = now or timezone.now()
    registrations = EventRegistration.objects.filter(
        status=Registered,
        reminder_sent_at__isnull=True,
        event__status=Event.Status.PUBLISHED,
        event__hidden_by_moderation=False,
        event__starts_at__gt=now,
        event__starts_at__lte=now + REMINDER_WINDOW,
    ).select_related("event", "user")
    sent = 0
    for registration in registrations:
        notify(
            registration.user,
            type=Notification.Type.EVENT_REMINDER,
            title=f"Rappel : « {registration.event.title} » commence bientôt",
            target_url=event_url(registration.event),
        )
        registration.reminder_sent_at = now
        registration.save(update_fields=["reminder_sent_at", "updated_at"])
        sent += 1
    return sent
