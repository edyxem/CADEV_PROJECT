"""Opportunités (emplois, stages, bourses…) et organisations vérifiées (P2, module L)."""

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.catalog.models import Country, Technology
from apps.profiles.models import ExperienceLevel
from apps.projects.models import Project
from common.models import BaseModel
from common.validators import validate_http_url


class Organization(BaseModel):
    """Organisation ou partenaire ; seule la vérification par un admin lui donne confiance."""

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    website = models.URLField(max_length=300, validators=[validate_http_url])
    description = models.TextField(blank=True, max_length=2000)
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="organizations", blank=True
    )
    is_verified = models.BooleanField("partenaire vérifié", default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "organisation"
        verbose_name_plural = "organisations"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Opportunity(BaseModel):
    class Type(models.TextChoices):
        JOB = "JOB", "Emploi"
        INTERNSHIP = "INTERNSHIP", "Stage"
        FREELANCE = "FREELANCE", "Mission freelance"
        SCHOLARSHIP = "SCHOLARSHIP", "Bourse"
        HACKATHON = "HACKATHON", "Hackathon"
        INCUBATION = "INCUBATION", "Programme d'incubation"
        TRAINING = "TRAINING", "Formation ou certification"
        CALL_FOR_PROJECTS = "CALL_FOR_PROJECTS", "Appel à projets"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Brouillon"
        PENDING_REVIEW = "PENDING_REVIEW", "En attente de validation"
        PUBLISHED = "PUBLISHED", "Publiée"
        REJECTED = "REJECTED", "Refusée"

    WorkMode = Project.CollaborationMode

    publisher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="opportunities"
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, null=True, blank=True, related_name="opportunities"
    )
    organization_name = models.CharField(
        max_length=120, blank=True, help_text="Si l'organisation n'est pas enregistrée."
    )
    type = models.CharField(max_length=20, choices=Type.choices)
    title = models.CharField(max_length=160)
    description = models.TextField()
    country = models.ForeignKey(
        Country, on_delete=models.SET_NULL, null=True, blank=True, related_name="opportunities"
    )
    location = models.CharField(max_length=120, blank=True)
    work_mode = models.CharField(max_length=8, choices=WorkMode.choices, default=WorkMode.REMOTE)
    level = models.CharField(max_length=16, choices=ExperienceLevel.choices, blank=True)
    technologies = models.ManyToManyField(Technology, blank=True, related_name="opportunities")
    deadline = models.DateField("date limite", null=True, blank=True)
    application_url = models.URLField(max_length=300, blank=True, validators=[validate_http_url])
    contact_email = models.EmailField(blank=True)
    source_url = models.URLField(
        "source officielle",
        max_length=300,
        validators=[validate_http_url],
        help_text="Lien permettant de vérifier l'annonce (obligatoire).",
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    review_note = models.CharField(max_length=500, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    published_at = models.DateTimeField(null=True, blank=True)
    hidden_by_moderation = models.BooleanField(default=False)

    class Meta:
        verbose_name = "opportunité"
        verbose_name_plural = "opportunités"
        ordering = ["-published_at", "-created_at"]
        indexes = [models.Index(fields=["status", "deadline"], name="opportunity_list_idx")]
        constraints = [
            models.CheckConstraint(
                condition=~Q(organization__isnull=True, organization_name=""),
                name="opportunity_has_organization",
            ),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def organization_label(self) -> str:
        return self.organization.name if self.organization else self.organization_name

    @property
    def is_expired(self) -> bool:
        return self.deadline is not None and self.deadline < timezone.localdate()

    @property
    def is_publicly_visible(self) -> bool:
        return self.status == self.Status.PUBLISHED and not self.hidden_by_moderation


OPPORTUNITY_TRANSITIONS: dict[str, set[str]] = {
    Opportunity.Status.DRAFT: {Opportunity.Status.PENDING_REVIEW, Opportunity.Status.PUBLISHED},
    Opportunity.Status.PENDING_REVIEW: {
        Opportunity.Status.PUBLISHED,
        Opportunity.Status.REJECTED,
        Opportunity.Status.DRAFT,
    },
    Opportunity.Status.REJECTED: {Opportunity.Status.DRAFT, Opportunity.Status.PENDING_REVIEW},
    Opportunity.Status.PUBLISHED: {Opportunity.Status.DRAFT},
}


class OpportunityInterest(BaseModel):
    """Intention de candidater ou demande d'information (pas de recrutement de bout en bout)."""

    class Kind(models.TextChoices):
        APPLICATION = "APPLICATION", "Je candidate"
        INFORMATION = "INFORMATION", "Demande d'information"

    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name="interests")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="opportunity_interests"
    )
    kind = models.CharField(max_length=12, choices=Kind.choices)
    message = models.TextField(max_length=2000)

    class Meta:
        verbose_name = "intérêt pour une opportunité"
        verbose_name_plural = "intérêts pour des opportunités"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["opportunity", "user", "kind"], name="opportunity_interest_unique"
            ),
        ]
