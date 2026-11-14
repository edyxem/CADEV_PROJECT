"""Notifications internes, personnelles et sans donnée sensible."""

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models

from common.models import BaseModel


class Notification(BaseModel):
    class Type(models.TextChoices):
        ANSWER_CREATED = "ANSWER_CREATED", "Nouvelle réponse à votre question"
        COMMENT_CREATED = "COMMENT_CREATED", "Nouveau commentaire sur votre publication"
        COMMENT_REPLY = "COMMENT_REPLY", "Réponse à votre commentaire"
        ANSWER_ACCEPTED = "ANSWER_ACCEPTED", "Votre réponse a été acceptée"
        VOTE_MILESTONE = "VOTE_MILESTONE", "Palier de votes atteint"
        JOIN_REQUEST_RECEIVED = "JOIN_REQUEST_RECEIVED", "Demande pour rejoindre votre projet"
        JOIN_REQUEST_ACCEPTED = "JOIN_REQUEST_ACCEPTED", "Demande acceptée"
        JOIN_REQUEST_REJECTED = "JOIN_REQUEST_REJECTED", "Demande refusée"
        TASK_ASSIGNED = "TASK_ASSIGNED", "Tâche assignée"
        PROJECT_UPDATED = "PROJECT_UPDATED", "Modification importante d'un projet"
        PROJECT_INVITATION = "PROJECT_INVITATION", "Invitation à rejoindre un projet"
        MODERATION_ACTION = "MODERATION_ACTION", "Décision de modération"
        NEW_FOLLOWER = "NEW_FOLLOWER", "Nouvel abonné"
        ACHIEVEMENT_AWARDED = "ACHIEVEMENT_AWARDED", "Nouveau badge"
        MESSAGE_RECEIVED = "MESSAGE_RECEIVED", "Nouveau message privé"
        MENTORSHIP_UPDATE = "MENTORSHIP_UPDATE", "Mise à jour de mentorat"
        EVENT_REMINDER = "EVENT_REMINDER", "Rappel d'événement"
        OPPORTUNITY_UPDATE = "OPPORTUNITY_UPDATE", "Mise à jour d'opportunité"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    type = models.CharField(max_length=32, choices=Type.choices, db_index=True)
    title = models.CharField(max_length=140)
    message = models.CharField(max_length=300, blank=True)
    target_type = models.CharField(max_length=32, blank=True)
    target_id = models.UUIDField(null=True, blank=True)
    target_url = models.CharField(
        max_length=200, blank=True, help_text="Chemin relatif de la page frontend concernée."
    )
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "notification"
        verbose_name_plural = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read", "-created_at"], name="notif_inbox_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.recipient} — {self.title}"


# Une décision de modération doit toujours parvenir au membre concerné (§Q.4).
MANDATORY_TYPES = frozenset({Notification.Type.MODERATION_ACTION})


class NotificationPreference(BaseModel):
    """Paramètres de notification d'un membre (P1)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_preferences"
    )
    muted_types = ArrayField(
        models.CharField(max_length=32, choices=Notification.Type.choices),
        default=list,
        blank=True,
        help_text="Types de notification que le membre ne souhaite plus recevoir.",
    )
    email_types = ArrayField(
        models.CharField(max_length=32, choices=Notification.Type.choices),
        default=list,
        blank=True,
        help_text="Types également envoyés par e-mail (P2).",
    )

    class Meta:
        verbose_name = "préférences de notification"
        verbose_name_plural = "préférences de notification"

    def __str__(self) -> str:
        return f"Préférences de {self.user}"
