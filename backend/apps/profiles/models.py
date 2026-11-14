"""Profil développeur, compétences déclarées et liens externes."""

import uuid

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MaxValueValidator
from django.db import models

from apps.catalog.models import Category, Country, Technology
from common.models import BaseModel
from common.validators import validate_http_url


def avatar_upload_path(instance: "DeveloperProfile", filename: str) -> str:
    """Nom de fichier aléatoire : le nom fourni par le client n'est jamais réutilisé."""
    extension = filename.rsplit(".", 1)[-1].lower()
    return f"avatars/{uuid.uuid4().hex}.{extension}"


class Language(models.TextChoices):
    FRENCH = "fr", "Français"
    ENGLISH = "en", "Anglais"
    PORTUGUESE = "pt", "Portugais"
    ARABIC = "ar", "Arabe"
    SWAHILI = "sw", "Swahili"
    HAUSA = "ha", "Haoussa"
    YORUBA = "yo", "Yoruba"
    WOLOF = "wo", "Wolof"
    AMHARIC = "am", "Amharique"
    LINGALA = "ln", "Lingala"
    BAMBARA = "bm", "Bambara"
    FULA = "ff", "Peul"


class ExperienceLevel(models.TextChoices):
    BEGINNER = "BEGINNER", "Débutant"
    INTERMEDIATE = "INTERMEDIATE", "Intermédiaire"
    ADVANCED = "ADVANCED", "Avancé"
    EXPERT = "EXPERT", "Expert"


class DeveloperProfile(BaseModel):
    """Vitrine publique d'un membre. Les niveaux sont toujours auto-évalués."""

    class Availability(models.TextChoices):
        NOT_AVAILABLE = "NOT_AVAILABLE", "Non disponible"
        OPEN_TO_COLLABORATION = "OPEN_TO_COLLABORATION", "Ouvert aux collaborations"
        LOOKING_FOR_PROJECT = "LOOKING_FOR_PROJECT", "Recherche un projet"
        AVAILABLE_FOR_MENTORING = "AVAILABLE_FOR_MENTORING", "Disponible pour du mentorat"

    class Visibility(models.TextChoices):
        PUBLIC = "PUBLIC", "Public"
        PRIVATE = "PRIVATE", "Privé"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    display_name = models.CharField("nom d'affichage", max_length=80)
    headline = models.CharField("titre", max_length=120, blank=True)
    bio = models.TextField("biographie", max_length=1000, blank=True)
    avatar = models.ImageField("avatar", upload_to=avatar_upload_path, blank=True)
    country = models.ForeignKey(
        Country, on_delete=models.SET_NULL, null=True, blank=True, related_name="profiles"
    )
    city = models.CharField("ville", max_length=80, blank=True)
    languages = ArrayField(
        models.CharField(max_length=2, choices=Language.choices), default=list, blank=True, size=8
    )
    experience_level = models.CharField(
        "niveau déclaré", max_length=16, choices=ExperienceLevel.choices, blank=True, db_index=True
    )
    availability_status = models.CharField(
        "disponibilité",
        max_length=32,
        choices=Availability.choices,
        default=Availability.NOT_AVAILABLE,
        db_index=True,
    )
    domains = models.ManyToManyField(Category, blank=True, related_name="profiles")
    profile_visibility = models.CharField(
        "visibilité du profil",
        max_length=8,
        choices=Visibility.choices,
        default=Visibility.PUBLIC,
        db_index=True,
    )
    show_city = models.BooleanField("ville visible", default=True)
    show_availability = models.BooleanField("disponibilité visible", default=True)
    show_reputation = models.BooleanField(
        "réputation, badges et recommandations visibles", default=True
    )

    class Meta:
        verbose_name = "profil développeur"
        verbose_name_plural = "profils développeurs"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.display_name or self.user.username

    @property
    def is_public(self) -> bool:
        return self.profile_visibility == self.Visibility.PUBLIC


class UserSkill(BaseModel):
    """Compétence déclarée. Le statut de vérification n'est jamais fixé par le membre."""

    class VerificationStatus(models.TextChoices):
        SELF_DECLARED = "SELF_DECLARED", "Auto-déclarée"
        EVIDENCE_ADDED = "EVIDENCE_ADDED", "Preuve ajoutée (non vérifiée)"
        PEER_REVIEWED = "PEER_REVIEWED", "Validée par des pairs"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="skills"
    )
    technology = models.ForeignKey(Technology, on_delete=models.PROTECT, related_name="user_skills")
    level = models.CharField("niveau auto-déclaré", max_length=16, choices=ExperienceLevel.choices)
    years_experience = models.PositiveSmallIntegerField(
        "années d'expérience", null=True, blank=True, validators=[MaxValueValidator(60)]
    )
    verification_status = models.CharField(
        max_length=16,
        choices=VerificationStatus.choices,
        default=VerificationStatus.SELF_DECLARED,
    )
    evidence_url = models.URLField("preuve", blank=True, validators=[validate_http_url])

    class Meta:
        verbose_name = "compétence"
        verbose_name_plural = "compétences"
        ordering = ["technology__name"]
        constraints = [
            models.UniqueConstraint(fields=["user", "technology"], name="profiles_skill_unique"),
            models.CheckConstraint(
                condition=models.Q(years_experience__isnull=True)
                | models.Q(years_experience__lte=60),
                name="profiles_skill_years_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user} — {self.technology}"


class SocialLink(BaseModel):
    """Lien externe déclaré. Un lien ne vaut jamais vérification d'une compétence."""

    class Platform(models.TextChoices):
        GITHUB = "GITHUB", "GitHub"
        GITLAB = "GITLAB", "GitLab"
        LINKEDIN = "LINKEDIN", "LinkedIn"
        PORTFOLIO = "PORTFOLIO", "Portfolio"
        WEBSITE = "WEBSITE", "Site personnel"
        X = "X", "X / Twitter"
        STACKOVERFLOW = "STACKOVERFLOW", "Stack Overflow"
        OTHER = "OTHER", "Autre"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="social_links"
    )
    platform = models.CharField(max_length=16, choices=Platform.choices)
    url = models.URLField(max_length=300, validators=[validate_http_url])
    is_public = models.BooleanField("public", default=True)

    class Meta:
        verbose_name = "lien externe"
        verbose_name_plural = "liens externes"
        ordering = ["platform", "created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "url"], name="profiles_link_unique_url"),
        ]

    def __str__(self) -> str:
        return f"{self.get_platform_display()} — {self.url}"


class PortfolioItem(BaseModel):
    """Réalisation présentée sur le profil (P2) ; un lien n'en fait pas une preuve vérifiée."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="portfolio_items"
    )
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True, max_length=2000)
    url = models.URLField(max_length=300, blank=True, validators=[validate_http_url])
    technologies = models.ManyToManyField(Technology, blank=True, related_name="portfolio_items")
    project = models.ForeignKey(
        "projects.Project", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "réalisation"
        verbose_name_plural = "réalisations"
        ordering = ["sort_order", "-created_at"]

    def __str__(self) -> str:
        return self.title
