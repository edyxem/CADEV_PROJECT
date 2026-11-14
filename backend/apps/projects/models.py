"""Projets, équipe, rôles recherchés, demandes pour rejoindre et tâches."""

import uuid

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from apps.catalog.models import Category, Technology
from common.models import BaseModel
from common.validators import validate_http_url


def logo_upload_path(instance: "Project", filename: str) -> str:
    return f"project-logos/{uuid.uuid4().hex}.webp"


class Project(BaseModel):
    class Status(models.TextChoices):
        IDEA = "IDEA", "Idée"
        RECRUITING = "RECRUITING", "Recherche d'équipe"
        IN_PROGRESS = "IN_PROGRESS", "En cours"
        PAUSED = "PAUSED", "Suspendu"
        COMPLETED = "COMPLETED", "Terminé"
        ARCHIVED = "ARCHIVED", "Archivé"

    class Visibility(models.TextChoices):
        PUBLIC = "PUBLIC", "Public"
        PRIVATE = "PRIVATE", "Privé (membres uniquement)"

    class CollaborationMode(models.TextChoices):
        REMOTE = "REMOTE", "À distance"
        HYBRID = "HYBRID", "Hybride"
        ONSITE = "ONSITE", "Présentiel"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="owned_projects"
    )
    name = models.CharField("nom", max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    short_description = models.CharField("résumé", max_length=240)
    description = models.TextField("description", blank=True)
    problem = models.TextField("problématique ou besoin visé", blank=True, max_length=3000)
    objectives = models.TextField("objectifs et résultat recherché", blank=True, max_length=3000)
    logo = models.ImageField(upload_to=logo_upload_path, blank=True)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="projects"
    )
    technologies = models.ManyToManyField(Technology, blank=True, related_name="projects")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.RECRUITING)
    visibility = models.CharField(
        max_length=8, choices=Visibility.choices, default=Visibility.PUBLIC
    )
    collaboration_mode = models.CharField(
        max_length=8, choices=CollaborationMode.choices, default=CollaborationMode.REMOTE
    )
    expected_availability = models.CharField(
        "disponibilité attendue", max_length=120, blank=True, help_text="Ex. 5 h par semaine."
    )
    accepts_join_requests = models.BooleanField("candidatures ouvertes", default=True)
    repository_url = models.URLField(max_length=300, blank=True, validators=[validate_http_url])
    demo_url = models.URLField(max_length=300, blank=True, validators=[validate_http_url])
    completed_at = models.DateTimeField(null=True, blank=True)
    hidden_by_moderation = models.BooleanField(
        "masqué par la modération",
        default=False,
        help_text="Retiré des espaces publics ; seuls ses membres et la modération le voient.",
    )

    class Meta:
        verbose_name = "projet"
        verbose_name_plural = "projets"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["visibility", "status", "-created_at"], name="project_list_idx"),
            models.Index(fields=["owner"], name="project_owner_idx"),
            GinIndex(fields=["name"], opclasses=["gin_trgm_ops"], name="project_name_trgm_idx"),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def is_public(self) -> bool:
        return self.visibility == self.Visibility.PUBLIC


# Transitions autorisées du statut d'un projet (§11.11).
PROJECT_TRANSITIONS: dict[str, set[str]] = {
    Project.Status.IDEA: {
        Project.Status.RECRUITING,
        Project.Status.IN_PROGRESS,
        Project.Status.PAUSED,
        Project.Status.ARCHIVED,
    },
    Project.Status.RECRUITING: {
        Project.Status.IDEA,
        Project.Status.IN_PROGRESS,
        Project.Status.PAUSED,
        Project.Status.ARCHIVED,
    },
    Project.Status.IN_PROGRESS: {
        Project.Status.RECRUITING,
        Project.Status.PAUSED,
        Project.Status.COMPLETED,
        Project.Status.ARCHIVED,
    },
    Project.Status.PAUSED: {
        Project.Status.RECRUITING,
        Project.Status.IN_PROGRESS,
        Project.Status.ARCHIVED,
    },
    Project.Status.COMPLETED: {Project.Status.IN_PROGRESS, Project.Status.ARCHIVED},
    Project.Status.ARCHIVED: {Project.Status.PAUSED},
}

# Statuts dans lesquels un projet accepte de nouveaux membres.
JOINABLE_STATUSES = {Project.Status.IDEA, Project.Status.RECRUITING, Project.Status.IN_PROGRESS}
# Statuts figés : plus aucune tâche ni modification de l'équipe.
FROZEN_STATUSES = {Project.Status.ARCHIVED}


class ProjectMember(BaseModel):
    """Appartenance à un projet. Le rôle projet ne donne aucun privilège global (§3.3)."""

    class Role(models.TextChoices):
        OWNER = "OWNER", "Propriétaire"
        MANAGER = "MANAGER", "Responsable"
        CONTRIBUTOR = "CONTRIBUTOR", "Contributeur"
        OBSERVER = "OBSERVER", "Observateur"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Actif"
        LEFT = "LEFT", "Parti"
        REMOVED = "REMOVED", "Retiré"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_memberships"
    )
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.CONTRIBUTOR)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.ACTIVE)
    title = models.CharField(
        "intitulé", max_length=80, blank=True, help_text="Ex. Développeuse backend."
    )
    can_manage_members = models.BooleanField(
        "peut gérer les membres",
        default=False,
        help_text="Droit accordé par le propriétaire à un responsable.",
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "membre de projet"
        verbose_name_plural = "membres de projet"
        ordering = ["joined_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "user"],
                condition=Q(status="ACTIVE"),
                name="project_member_one_active",
            ),
            models.UniqueConstraint(
                fields=["project"],
                condition=Q(status="ACTIVE", role="OWNER"),
                name="project_single_owner",
            ),
        ]
        indexes = [models.Index(fields=["user", "status"], name="member_user_idx")]

    def __str__(self) -> str:
        return f"{self.user} — {self.project} ({self.get_role_display()})"

    @property
    def is_active(self) -> bool:
        return self.status == self.Status.ACTIVE


class ProjectRoleNeed(BaseModel):
    """Rôle recherché par un projet (frontend, backend, UI/UX, réseau, data…)."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="role_needs")
    role_name = models.CharField("rôle", max_length=80)
    description = models.TextField(blank=True, max_length=1000)
    expected_level = models.CharField("niveau attendu", max_length=40, blank=True)
    required_technologies = models.ManyToManyField(
        Technology, blank=True, related_name="role_needs"
    )
    slots = models.PositiveSmallIntegerField(
        "places", default=1, validators=[MinValueValidator(1), MaxValueValidator(20)]
    )
    is_open = models.BooleanField("ouvert", default=True)

    class Meta:
        verbose_name = "rôle recherché"
        verbose_name_plural = "rôles recherchés"
        ordering = ["created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(slots__gte=1) & Q(slots__lte=20), name="role_need_slots_range"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.role_name} — {self.project}"


class JoinRequest(BaseModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "En attente"
        ACCEPTED = "ACCEPTED", "Acceptée"
        REJECTED = "REJECTED", "Refusée"
        WITHDRAWN = "WITHDRAWN", "Retirée"

    MESSAGE_MIN_LENGTH = 20

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="join_requests")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="join_requests"
    )
    requested_role = models.ForeignKey(
        ProjectRoleNeed,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="join_requests",
    )
    message = models.TextField("motivation", max_length=2000)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    response_message = models.CharField("réponse au candidat", max_length=500, blank=True)
    can_reapply = models.BooleanField(
        "nouvelle demande autorisée",
        default=False,
        help_text="Après un refus, permet au candidat de redemander sans attendre le délai.",
    )

    class Meta:
        verbose_name = "demande pour rejoindre"
        verbose_name_plural = "demandes pour rejoindre"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "user"],
                condition=Q(status="PENDING"),
                name="join_request_one_pending",
            ),
        ]
        indexes = [models.Index(fields=["project", "status"], name="join_request_project_idx")]

    def __str__(self) -> str:
        return f"{self.user} → {self.project} ({self.get_status_display()})"


JOIN_REQUEST_TRANSITIONS: dict[str, set[str]] = {
    JoinRequest.Status.PENDING: {
        JoinRequest.Status.ACCEPTED,
        JoinRequest.Status.REJECTED,
        JoinRequest.Status.WITHDRAWN,
    },
    JoinRequest.Status.ACCEPTED: set(),
    JoinRequest.Status.REJECTED: set(),
    JoinRequest.Status.WITHDRAWN: set(),
}


class ProjectTask(BaseModel):
    class Status(models.TextChoices):
        TODO = "TODO", "À faire"
        IN_PROGRESS = "IN_PROGRESS", "En cours"
        IN_REVIEW = "IN_REVIEW", "En revue"
        DONE = "DONE", "Terminée"
        BLOCKED = "BLOCKED", "Bloquée"

    class Priority(models.TextChoices):
        LOW = "LOW", "Basse"
        MEDIUM = "MEDIUM", "Moyenne"
        HIGH = "HIGH", "Haute"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True, max_length=5000)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_tasks"
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.TODO)
    priority = models.CharField(max_length=8, choices=Priority.choices, default=Priority.MEDIUM)
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "tâche"
        verbose_name_plural = "tâches"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["project", "status"], name="task_project_idx"),
            models.Index(fields=["assignee", "status"], name="task_assignee_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~Q(status="DONE") | Q(completed_at__isnull=False),
                name="task_done_has_date",
            ),
        ]

    def __str__(self) -> str:
        return self.title


TASK_TRANSITIONS: dict[str, set[str]] = {
    ProjectTask.Status.TODO: {
        ProjectTask.Status.IN_PROGRESS,
        ProjectTask.Status.BLOCKED,
        ProjectTask.Status.DONE,
    },
    ProjectTask.Status.IN_PROGRESS: {
        ProjectTask.Status.TODO,
        ProjectTask.Status.IN_REVIEW,
        ProjectTask.Status.BLOCKED,
        ProjectTask.Status.DONE,
    },
    ProjectTask.Status.IN_REVIEW: {
        ProjectTask.Status.IN_PROGRESS,
        ProjectTask.Status.DONE,
        ProjectTask.Status.BLOCKED,
    },
    ProjectTask.Status.BLOCKED: {ProjectTask.Status.TODO, ProjectTask.Status.IN_PROGRESS},
    ProjectTask.Status.DONE: {ProjectTask.Status.IN_PROGRESS},
}
