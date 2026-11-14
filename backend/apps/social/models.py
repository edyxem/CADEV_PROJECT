"""Abonnements à des membres, technologies ou catégories (P1, module K)."""

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.catalog.models import Category, Technology
from common.models import BaseModel


class Follow(BaseModel):
    class TargetType(models.TextChoices):
        USER = "USER", "Membre"
        TECHNOLOGY = "TECHNOLOGY", "Technologie"
        CATEGORY = "CATEGORY", "Catégorie"

    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="following"
    )
    target_type = models.CharField(max_length=12, choices=TargetType.choices)
    followed_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="followers",
    )
    technology = models.ForeignKey(
        Technology, on_delete=models.CASCADE, null=True, blank=True, related_name="followers"
    )
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, null=True, blank=True, related_name="followers"
    )

    class Meta:
        verbose_name = "abonnement"
        verbose_name_plural = "abonnements"
        ordering = ["-created_at"]
        constraints = [
            # Exactement une cible, cohérente avec ``target_type``.
            models.CheckConstraint(
                condition=(
                    Q(
                        target_type="USER",
                        followed_user__isnull=False,
                        technology__isnull=True,
                        category__isnull=True,
                    )
                    | Q(
                        target_type="TECHNOLOGY",
                        followed_user__isnull=True,
                        technology__isnull=False,
                        category__isnull=True,
                    )
                    | Q(
                        target_type="CATEGORY",
                        followed_user__isnull=True,
                        technology__isnull=True,
                        category__isnull=False,
                    )
                ),
                name="follow_exactly_one_target",
            ),
            models.CheckConstraint(
                condition=~Q(follower=models.F("followed_user")), name="follow_not_self"
            ),
            models.UniqueConstraint(
                fields=["follower", "followed_user"],
                condition=Q(target_type="USER"),
                name="follow_unique_user",
            ),
            models.UniqueConstraint(
                fields=["follower", "technology"],
                condition=Q(target_type="TECHNOLOGY"),
                name="follow_unique_technology",
            ),
            models.UniqueConstraint(
                fields=["follower", "category"],
                condition=Q(target_type="CATEGORY"),
                name="follow_unique_category",
            ),
        ]

    def __str__(self) -> str:
        target = self.followed_user or self.technology or self.category
        return f"{self.follower} suit {target}"
