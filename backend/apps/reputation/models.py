"""Événements de contribution, badges et recommandations (P1, module I)."""

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.catalog.models import Technology
from common.models import BaseModel


class EventType(models.TextChoices):
    ANSWER_ACCEPTED = "ANSWER_ACCEPTED", "Réponse acceptée"
    ANSWER_UPVOTED = "ANSWER_UPVOTED", "Vote utile reçu sur une réponse"
    POST_UPVOTED = "POST_UPVOTED", "Vote utile reçu sur une publication"
    ARTICLE_PUBLISHED = "ARTICLE_PUBLISHED", "Tutoriel publié"
    TASK_COMPLETED = "TASK_COMPLETED", "Tâche de projet terminée"
    PROJECT_COMPLETED = "PROJECT_COMPLETED", "Projet terminé"
    RECOMMENDATION_RECEIVED = "RECOMMENDATION_RECEIVED", "Recommandation reçue"
    MENTORSHIP_COMPLETED = "MENTORSHIP_COMPLETED", "Mentorat terminé"


class ContributionEvent(BaseModel):
    """Contribution réelle et vérifiable ; la réputation est la somme de leurs points.

    Ces lignes sont dérivées des données sources par ``services.sync_user`` :
    elles peuvent être recalculées à tout moment et ne sont jamais saisies.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="contribution_events"
    )
    event_type = models.CharField(max_length=32, choices=EventType.choices)
    object_type = models.CharField(max_length=32)
    object_id = models.UUIDField()
    points = models.PositiveSmallIntegerField()

    class Meta:
        verbose_name = "événement de contribution"
        verbose_name_plural = "événements de contribution"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "event_type", "object_id"], name="contribution_event_unique"
            ),
        ]
        indexes = [models.Index(fields=["user", "event_type"], name="contribution_user_idx")]

    def __str__(self) -> str:
        return f"{self.user} — {self.get_event_type_display()} (+{self.points})"


class Achievement(BaseModel):
    """Badge attribué selon un seuil explicite sur un type d'événement."""

    code = models.SlugField("code de règle", max_length=40, unique=True)
    name = models.CharField(max_length=80)
    description = models.CharField(max_length=240)
    icon_key = models.CharField(max_length=40, blank=True)
    event_type = models.CharField(max_length=32, choices=EventType.choices)
    threshold = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "badge"
        verbose_name_plural = "badges"
        ordering = ["event_type", "threshold"]

    def __str__(self) -> str:
        return self.name


class UserAchievement(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="achievements"
    )
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE, related_name="holders")
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "badge obtenu"
        verbose_name_plural = "badges obtenus"
        ordering = ["-awarded_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "achievement"], name="user_achievement_unique"),
        ]


class Recommendation(BaseModel):
    """Recommandation contextualisée d'un membre par un autre (jamais par soi-même)."""

    CONTEXT_MIN_LENGTH = 30

    recommender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recommendations_given"
    )
    recommended = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recommendations_received"
    )
    technology = models.ForeignKey(
        Technology, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    context = models.TextField("contexte de la collaboration", max_length=1000)

    class Meta:
        verbose_name = "recommandation"
        verbose_name_plural = "recommandations"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["recommender", "recommended"], name="recommendation_unique_pair"
            ),
            models.CheckConstraint(
                condition=~Q(recommender=models.F("recommended")), name="recommendation_not_self"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.recommender} recommande {self.recommended}"
