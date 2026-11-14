"""Signalements, actions de modération et journal d'audit."""

from django.conf import settings
from django.db import models
from django.db.models import Q

from common.models import BaseModel


class TargetType(models.TextChoices):
    POST = "POST", "Publication"
    COMMENT = "COMMENT", "Commentaire"
    ANSWER = "ANSWER", "Réponse"
    PROFILE = "PROFILE", "Profil / compte"
    PROJECT = "PROJECT", "Projet"
    OPPORTUNITY = "OPPORTUNITY", "Opportunité"
    MESSAGE = "MESSAGE", "Message privé"
    EVENT = "EVENT", "Événement"
    COMMUNITY = "COMMUNITY", "Communauté"


class Report(BaseModel):
    class Reason(models.TextChoices):
        SPAM = "SPAM", "Spam"
        SCAM = "SCAM", "Arnaque ou offre trompeuse"
        HARASSMENT = "HARASSMENT", "Harcèlement ou intimidation"
        HATE = "HATE", "Contenu haineux ou discriminatoire"
        IMPERSONATION = "IMPERSONATION", "Usurpation d'identité"
        DANGEROUS = "DANGEROUS", "Contenu dangereux ou illégal"
        INTELLECTUAL_PROPERTY = "INTELLECTUAL_PROPERTY", "Violation de propriété intellectuelle"
        OTHER = "OTHER", "Autre motif"

    class Status(models.TextChoices):
        PENDING = "PENDING", "En attente"
        REVIEWING = "REVIEWING", "En cours d'examen"
        ACTION_TAKEN = "ACTION_TAKEN", "Action prise"
        REJECTED = "REJECTED", "Rejeté"
        CLOSED = "CLOSED", "Clôturé"

    OPEN_STATUSES = ("PENDING", "REVIEWING")

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reports"
    )
    target_type = models.CharField(max_length=16, choices=TargetType.choices)
    target_id = models.UUIDField()
    reason = models.CharField(max_length=24, choices=Reason.choices)
    details = models.TextField("précisions", blank=True, max_length=2000)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_reports",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.CharField(max_length=500, blank=True)

    class Meta:
        verbose_name = "signalement"
        verbose_name_plural = "signalements"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"], name="report_queue_idx"),
            models.Index(fields=["target_type", "target_id"], name="report_target_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["reporter", "target_type", "target_id"],
                condition=Q(status__in=["PENDING", "REVIEWING"]),
                name="report_one_open_per_reporter_target",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_reason_display()} — {self.get_target_type_display()} {self.target_id}"


# Workflow §Q.3 : créé → en attente → en examen → action prise ou rejeté → clôturé.
REPORT_TRANSITIONS: dict[str, set[str]] = {
    Report.Status.PENDING: {
        Report.Status.REVIEWING,
        Report.Status.ACTION_TAKEN,
        Report.Status.REJECTED,
    },
    Report.Status.REVIEWING: {
        Report.Status.PENDING,
        Report.Status.ACTION_TAKEN,
        Report.Status.REJECTED,
    },
    Report.Status.ACTION_TAKEN: {Report.Status.CLOSED},
    Report.Status.REJECTED: {Report.Status.CLOSED},
    Report.Status.CLOSED: set(),
}


class ModerationAction(BaseModel):
    """Trace immuable de chaque décision : auteur, date, motif, cible (§Q.4)."""

    class ActionType(models.TextChoices):
        NO_ACTION = "NO_ACTION", "Aucune action (signalement rejeté)"
        WARNING = "WARNING", "Avertissement"
        HIDE = "HIDE", "Masquage"
        RESTORE = "RESTORE", "Restauration"
        DELETE = "DELETE", "Suppression logique"
        SUSPEND = "SUSPEND", "Suspension temporaire du compte"
        UNSUSPEND = "UNSUSPEND", "Levée de suspension"
        BAN = "BAN", "Bannissement"
        UNBAN = "UNBAN", "Levée de bannissement"

    report = models.ForeignKey(
        Report, on_delete=models.SET_NULL, null=True, blank=True, related_name="actions"
    )
    moderator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="moderation_actions"
    )
    target_type = models.CharField(max_length=16, choices=TargetType.choices)
    target_id = models.UUIDField()
    action_type = models.CharField(max_length=16, choices=ActionType.choices)
    reason = models.CharField("motif", max_length=1000)
    previous_state = models.CharField(max_length=32, blank=True)
    new_state = models.CharField(max_length=32, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "action de modération"
        verbose_name_plural = "actions de modération"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["target_type", "target_id"], name="modaction_target_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.get_action_type_display()} par {self.moderator}"


class AuditLog(BaseModel):
    """Journal des actions sensibles (modération, rôles, comptes). En ajout seul."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_entries",
    )
    action = models.CharField(max_length=64, db_index=True)
    target_type = models.CharField(max_length=32, blank=True)
    target_id = models.CharField(max_length=64, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "entrée du journal d'audit"
        verbose_name_plural = "journal d'audit"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.action} — {self.target_type} {self.target_id}"
