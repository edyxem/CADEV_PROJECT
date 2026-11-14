"""Droits liés au rôle dans un projet, distincts des rôles globaux (§3.3, §H.4).

| Rôle projet   | Paramètres | Membres                   | Tâches                            |
|---------------|------------|---------------------------|-----------------------------------|
| Propriétaire  | oui        | oui                       | toutes                            |
| Responsable   | non        | si ``can_manage_members`` | toutes                            |
| Contributeur  | non        | non                       | créer ; modifier les siennes      |
| Observateur   | non        | non                       | lecture seule                     |
"""

from typing import Any

from django.http import Http404
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request

from common.permissions import is_moderator

from .models import Project, ProjectMember, ProjectTask

Role = ProjectMember.Role


def membership(project: Project, user: Any) -> ProjectMember | None:
    """Appartenance active du membre au projet, mise en cache sur l'instance."""
    if user is None or not user.is_authenticated:
        return None
    cache = project.__dict__.setdefault("_membership_cache", {})
    if user.pk not in cache:
        cache[user.pk] = ProjectMember.objects.filter(
            project=project, user=user, status=ProjectMember.Status.ACTIVE
        ).first()
    return cache[user.pk]


def role_of(project: Project, user: Any) -> str | None:
    member = membership(project, user)
    return member.role if member else None


def can_view(project: Project, user: Any) -> bool:
    return project.is_public or is_moderator(user) or membership(project, user) is not None


def is_owner(project: Project, user: Any) -> bool:
    return role_of(project, user) == Role.OWNER


def can_edit_settings(project: Project, user: Any) -> bool:
    return is_owner(project, user)


def can_manage_members(project: Project, user: Any) -> bool:
    member = membership(project, user)
    if member is None:
        return False
    return member.role == Role.OWNER or (member.role == Role.MANAGER and member.can_manage_members)


def can_manage_tasks(project: Project, user: Any) -> bool:
    return role_of(project, user) in {Role.OWNER, Role.MANAGER}


def can_contribute(project: Project, user: Any) -> bool:
    return role_of(project, user) in {Role.OWNER, Role.MANAGER, Role.CONTRIBUTOR}


def can_view_tasks(project: Project, user: Any) -> bool:
    return membership(project, user) is not None or is_moderator(user)


def can_edit_task(task: ProjectTask, user: Any) -> bool:
    if can_manage_tasks(task.project, user):
        return True
    return role_of(task.project, user) == Role.CONTRIBUTOR and user.pk in {
        task.created_by_id,
        task.assignee_id,
    }


def ensure_can_view(project: Project, user: Any) -> None:
    """Un projet privé n'existe pas pour un non-membre (404 plutôt que 403)."""
    if not can_view(project, user):
        raise Http404


class IsProjectMember(BasePermission):
    message = "Réservé aux membres du projet."

    def has_object_permission(self, request: Request, view: Any, project: Project) -> bool:
        return membership(project, request.user) is not None


class IsProjectOwner(BasePermission):
    message = "Réservé au propriétaire du projet."

    def has_object_permission(self, request: Request, view: Any, project: Project) -> bool:
        return request.method in SAFE_METHODS or is_owner(project, request.user)


class IsProjectManagerOrOwner(BasePermission):
    message = "Réservé au propriétaire ou aux responsables habilités du projet."

    def has_object_permission(self, request: Request, view: Any, project: Project) -> bool:
        return can_manage_members(project, request.user)
