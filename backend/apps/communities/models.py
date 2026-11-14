"""Communautés par pays, ville, université, technologie ou domaine (P2, module N)."""

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.catalog.models import Category, Country, Technology
from common.models import BaseModel


class Community(BaseModel):
    class Kind(models.TextChoices):
        COUNTRY = "COUNTRY", "Pays"
        CITY = "CITY", "Ville"
        UNIVERSITY = "UNIVERSITY", "Université"
        TECHNOLOGY = "TECHNOLOGY", "Technologie"
        DOMAIN = "DOMAIN", "Domaine"

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    kind = models.CharField(max_length=12, choices=Kind.choices)
    description = models.TextField(max_length=2000)
    rules = models.TextField(
        "règles locales",
        blank=True,
        max_length=3000,
        help_text="Elles complètent les règles générales de la plateforme, sans les contredire.",
    )
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True)
    city = models.CharField(max_length=80, blank=True)
    technology = models.ForeignKey(Technology, on_delete=models.SET_NULL, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_communities"
    )
    hidden_by_moderation = models.BooleanField(default=False)

    class Meta:
        verbose_name = "communauté"
        verbose_name_plural = "communautés"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class CommunityMembership(BaseModel):
    class Role(models.TextChoices):
        LEADER = "LEADER", "Responsable"
        MEMBER = "MEMBER", "Membre"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Actif"
        LEFT = "LEFT", "Parti"
        BANNED = "BANNED", "Exclu"

    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="community_memberships"
    )
    role = models.CharField(max_length=8, choices=Role.choices, default=Role.MEMBER)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        verbose_name = "membre de communauté"
        verbose_name_plural = "membres de communauté"
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["community", "user"],
                condition=Q(status__in=["ACTIVE", "BANNED"]),
                name="community_one_membership",
            ),
        ]
