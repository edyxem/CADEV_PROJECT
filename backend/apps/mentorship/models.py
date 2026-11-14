"""Mentorat volontaire : profils, demandes, sessions et retours (P2, module M)."""

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from apps.catalog.models import Category, Technology
from apps.profiles.models import Language
from common.models import BaseModel
from common.validators import validate_http_url


class MentorProfile(BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mentor_profile"
    )
    is_available = models.BooleanField("disponible", default=True)
    headline = models.CharField(max_length=160)
    bio = models.TextField(blank=True, max_length=2000)
    domains = models.ManyToManyField(Category, blank=True, related_name="mentors")
    technologies = models.ManyToManyField(Technology, blank=True, related_name="mentors")
    languages = ArrayField(
        models.CharField(max_length=2, choices=Language.choices), default=list, blank=True, size=8
    )
    max_active_mentees = models.PositiveSmallIntegerField(
        default=3, validators=[MinValueValidator(1), MaxValueValidator(20)]
    )

    class Meta:
        verbose_name = "profil de mentor"
        verbose_name_plural = "profils de mentor"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Mentor : {self.user}"


class MentorshipRequest(BaseModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "En attente"
        ACCEPTED = "ACCEPTED", "Acceptée"
        DECLINED = "DECLINED", "Déclinée"
        CANCELLED = "CANCELLED", "Annulée"
        COMPLETED = "COMPLETED", "Terminée"

    GOAL_MIN_LENGTH = 30

    mentee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mentorship_requests"
    )
    mentor = models.ForeignKey(MentorProfile, on_delete=models.CASCADE, related_name="requests")
    goal = models.TextField("objectif", max_length=2000)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    response_message = models.CharField(max_length=500, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "demande de mentorat"
        verbose_name_plural = "demandes de mentorat"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["mentee", "mentor"],
                condition=Q(status__in=["PENDING", "ACCEPTED"]),
                name="mentorship_one_open_request",
            ),
        ]


MENTORSHIP_TRANSITIONS: dict[str, set[str]] = {
    MentorshipRequest.Status.PENDING: {
        MentorshipRequest.Status.ACCEPTED,
        MentorshipRequest.Status.DECLINED,
        MentorshipRequest.Status.CANCELLED,
    },
    MentorshipRequest.Status.ACCEPTED: {
        MentorshipRequest.Status.COMPLETED,
        MentorshipRequest.Status.CANCELLED,
    },
    MentorshipRequest.Status.DECLINED: set(),
    MentorshipRequest.Status.CANCELLED: set(),
    MentorshipRequest.Status.COMPLETED: set(),
}


class MentorshipSession(BaseModel):
    class Status(models.TextChoices):
        PLANNED = "PLANNED", "Planifiée"
        COMPLETED = "COMPLETED", "Terminée"
        CANCELLED = "CANCELLED", "Annulée"

    request = models.ForeignKey(
        MentorshipRequest, on_delete=models.CASCADE, related_name="sessions"
    )
    scheduled_at = models.DateTimeField()
    duration_minutes = models.PositiveSmallIntegerField(
        default=60, validators=[MinValueValidator(15), MaxValueValidator(240)]
    )
    meeting_url = models.URLField(max_length=300, blank=True, validators=[validate_http_url])
    agenda = models.TextField(blank=True, max_length=2000)
    notes = models.TextField("notes partagées", blank=True, max_length=5000)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PLANNED)

    class Meta:
        verbose_name = "session de mentorat"
        verbose_name_plural = "sessions de mentorat"
        ordering = ["scheduled_at"]


SESSION_TRANSITIONS: dict[str, set[str]] = {
    MentorshipSession.Status.PLANNED: {
        MentorshipSession.Status.COMPLETED,
        MentorshipSession.Status.CANCELLED,
    },
    MentorshipSession.Status.COMPLETED: set(),
    MentorshipSession.Status.CANCELLED: set(),
}


class MentorshipFeedback(BaseModel):
    session = models.ForeignKey(
        MentorshipSession, on_delete=models.CASCADE, related_name="feedbacks"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mentorship_feedbacks"
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True, max_length=2000)

    class Meta:
        verbose_name = "retour de session"
        verbose_name_plural = "retours de session"
        constraints = [
            models.UniqueConstraint(
                fields=["session", "author"], name="mentorship_feedback_unique"
            ),
            models.CheckConstraint(
                condition=Q(rating__gte=1) & Q(rating__lte=5), name="mentorship_rating_range"
            ),
        ]
