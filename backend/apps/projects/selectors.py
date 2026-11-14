"""Requêtes de lecture des projets (visibilité et compteurs dérivés)."""

from typing import Any

from django.db.models import Case, Count, IntegerField, Prefetch, Q, QuerySet, Value, When

from apps.community.selectors import count_of
from common.permissions import is_moderator

from .models import JoinRequest, Project, ProjectMember, ProjectRoleNeed, ProjectTask

ACTIVE = ProjectMember.Status.ACTIVE


def _with_relations(queryset: QuerySet[Project]) -> QuerySet[Project]:
    return (
        queryset.select_related("owner__profile", "category")
        .prefetch_related(
            "technologies",
            Prefetch(
                "role_needs",
                queryset=ProjectRoleNeed.objects.prefetch_related("required_technologies"),
            ),
        )
        .annotate(
            member_count=count_of(ProjectMember.objects.filter(status=ACTIVE), "project"),
            open_role_count=count_of(ProjectRoleNeed.objects.filter(is_open=True), "project"),
        )
    )


def public_projects() -> QuerySet[Project]:
    """Projets publics non archivés : base de la liste et de la recherche."""
    return _with_relations(
        Project.objects.filter(visibility=Project.Visibility.PUBLIC).exclude(
            status=Project.Status.ARCHIVED
        )
    )


def visible_projects(user: Any) -> QuerySet[Project]:
    """Projets ouvrables en détail : publics, ou privés dont le lecteur est membre."""
    queryset = Project.objects.all()
    if not is_moderator(user):
        condition = Q(visibility=Project.Visibility.PUBLIC)
        if user is not None and user.is_authenticated:
            condition |= Q(memberships__user=user, memberships__status=ACTIVE)
        queryset = queryset.filter(condition).distinct()
    return _with_relations(queryset)


def my_projects(user: Any) -> QuerySet[Project]:
    return _with_relations(
        Project.objects.filter(memberships__user=user, memberships__status=ACTIVE).distinct()
    )


def task_stats(project: Project) -> dict[str, int]:
    rows = ProjectTask.objects.filter(project=project).values("status").annotate(total=Count("pk"))
    stats = dict.fromkeys(ProjectTask.Status.values, 0)
    stats.update({row["status"]: row["total"] for row in rows})
    stats["total"] = sum(stats[status] for status in ProjectTask.Status.values)
    return stats


def active_members(project: Project) -> QuerySet[ProjectMember]:
    role_rank = Case(
        When(role=ProjectMember.Role.OWNER, then=Value(0)),
        When(role=ProjectMember.Role.MANAGER, then=Value(1)),
        When(role=ProjectMember.Role.CONTRIBUTOR, then=Value(2)),
        default=Value(3),
        output_field=IntegerField(),
    )
    return (
        ProjectMember.objects.filter(project=project, status=ACTIVE)
        .select_related("user__profile")
        .annotate(role_rank=role_rank)
        .order_by("role_rank", "joined_at")
    )


def project_tasks(project: Project) -> QuerySet[ProjectTask]:
    priority_rank = Case(
        When(priority=ProjectTask.Priority.HIGH, then=Value(0)),
        When(priority=ProjectTask.Priority.MEDIUM, then=Value(1)),
        default=Value(2),
        output_field=IntegerField(),
    )
    return (
        ProjectTask.objects.filter(project=project)
        .select_related("assignee__profile", "created_by__profile")
        .annotate(priority_rank=priority_rank)
        .order_by("priority_rank", "due_date", "created_at")
    )


def project_join_requests(project: Project) -> QuerySet[JoinRequest]:
    return (
        JoinRequest.objects.filter(project=project)
        .select_related("user__profile", "requested_role", "reviewed_by")
        .order_by("-created_at")
    )
