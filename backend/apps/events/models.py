"""Événements communautaires et inscriptions (P2, module O)."""

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q

from apps.catalog.models import Category, Technology
from common.models import BaseModel
from common.validators import validate_http_url


class Event(BaseModel):
    class Format(models.TextChoices):
        ONLINE = "ONLINE", "En ligne"
        ONSITE = "ONSITE", "Présentiel"
        HYBRID = "HYBRID", "Hybride"

    class Kind(models.TextChoices):
        MEETUP = "MEETUP", "Meetup"
        WORKSHOP = "WORKSHOP", "Atelier"
        CONFERENCE = "CONFERENCE", "Conférence"
        WEBINAR = "WEBINAR", "Webinaire"
        COMPETITION = "COMPETITION", "Compétition"
        HACKATHON = "HACKATHON", "Hackathon"
        GROUP_MENTORING = "GROUP_MENTORING", "Mentorat collectif"

    class Status(models.TextChoices):
        PUBLISHED = "PUBLISHED", "Publié"
        CANCELLED = "CANCELLED", "Annulé"

    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="organized_events"
    )
    community = models.ForeignKey(
        "communities.Community",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
    )
    title = models.CharField(max_length=160)
    description = models.TextField()
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.MEETUP)
    format = models.CharField(max_length=8, choices=Format.choices, default=Format.ONLINE)
    starts_at = models.DateTimeField(db_index=True)
    ends_at = models.DateTimeField()
    location = models.CharField(max_length=200, blank=True)
    online_url = models.URLField(
        max_length=300,
        blank=True,
        validators=[validate_http_url],
        help_text="Communiqué uniquement aux inscrits.",
    )
    capacity = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(1)])
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    technologies = models.ManyToManyField(Technology, blank=True, related_name="events")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PUBLISHED)
    hidden_by_moderation = models.BooleanField(default=False)

    class Meta:
        verbose_name = "événement"
        verbose_name_plural = "événements"
        ordering = ["starts_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_at__gt=F("starts_at")), name="event_ends_after_start"
            ),
        ]

    def __str__(self) -> str:
        return self.title


class EventRegistration(BaseModel):
    class Status(models.TextChoices):
        REGISTERED = "REGISTERED", "Inscrit"
        CANCELLED = "CANCELLED", "Désinscrit"

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="registrations")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="event_registrations"
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.REGISTERED)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "inscription"
        verbose_name_plural = "inscriptions"
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(fields=["event", "user"], name="event_registration_unique"),
        ]
