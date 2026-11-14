"""Référentiels administrables : catégories, tags, technologies et pays."""

from typing import Any

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower

from common.models import BaseModel

from .normalization import make_slug, normalize_label


class ActiveQuerySet(models.QuerySet):
    def active(self) -> "ActiveQuerySet":
        return self.filter(is_active=True)


class ReferenceItem(BaseModel):
    """Élément de référentiel : libellé normalisé, slug unique, désactivation logique."""

    name = models.CharField("nom", max_length=80)
    slug = models.SlugField("slug", max_length=90, unique=True)
    is_active = models.BooleanField("actif", default=True, db_index=True)

    objects = ActiveQuerySet.as_manager()

    class Meta:
        abstract = True
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        self.name = normalize_label(self.name)
        if not self.name:
            raise ValidationError({"name": "Le nom est obligatoire."})
        if not make_slug(self.name):
            raise ValidationError(
                {"name": "Le nom doit contenir au moins une lettre ou un chiffre."}
            )

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.name = normalize_label(self.name)
        if not self.slug:
            self.slug = make_slug(self.name)
        super().save(*args, **kwargs)


class Category(ReferenceItem):
    description = models.TextField("description", blank=True, max_length=500)
    sort_order = models.PositiveSmallIntegerField("ordre d'affichage", default=0)

    class Meta(ReferenceItem.Meta):
        verbose_name = "catégorie"
        verbose_name_plural = "catégories"
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(Lower("name"), name="catalog_category_name_ci_uniq"),
        ]


class Tag(ReferenceItem):
    class Meta(ReferenceItem.Meta):
        verbose_name = "tag"
        verbose_name_plural = "tags"
        constraints = [models.UniqueConstraint(Lower("name"), name="catalog_tag_name_ci_uniq")]


class Technology(ReferenceItem):
    category = models.ForeignKey(
        Category,
        verbose_name="catégorie",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="technologies",
    )

    class Meta(ReferenceItem.Meta):
        verbose_name = "technologie"
        verbose_name_plural = "technologies"
        constraints = [
            models.UniqueConstraint(Lower("name"), name="catalog_technology_name_ci_uniq"),
        ]


class Country(BaseModel):
    """Pays normalisé par son code ISO 3166-1 alpha-2."""

    code = models.CharField("code ISO", max_length=2, unique=True)
    name = models.CharField("nom", max_length=80, unique=True)
    is_active = models.BooleanField("actif", default=True, db_index=True)

    objects = ActiveQuerySet.as_manager()

    class Meta:
        verbose_name = "pays"
        verbose_name_plural = "pays"
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(code__regex=r"^[A-Z]{2}$"), name="catalog_country_code_iso2"
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.code = (self.code or "").strip().upper()
        super().save(*args, **kwargs)
