"""Règles métier de la collaboration : projets, demandes, membres et tâches."""

from datetime import timedelta
from typing import Any

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import exceptions

from apps.accounts.models import User
from apps.catalog.normalization import make_slug
from apps.notifications.models import Notification
from apps.notifications.services import notify
from common.exceptions import BusinessRuleViolation
from common.images import remove_image, replace_image
from common.sanitization import sanitize_rich_text, to_plain_text
from common.transitions import ensure_transition

from . import policies
from .models import (
    FROZEN_STATUSES,
    JOIN_REQUEST_TRANSITIONS,
    JOINABLE_STATUSES,
    PROJECT_TRANSITIONS,
    TASK_TRANSITIONS,
    JoinRequest,
    Project,
    ProjectMember,
    ProjectRoleNeed,
    ProjectTask,
)

REAPPLY_COOLDOWN = timedelta(days=30)
LOGO_SIZE = (512, 512)
MANAGER_ROLES = {ProjectMember.Role.OWNER, ProjectMember.Role.MANAGER}
Role = ProjectMember.Role


def project_url(project: Project) -> str:
    return f"/projets/{project.slug}"


def _forbid(message: str) -> None:
    raise exceptions.PermissionDenied(message)


def _unique_slug(name: str) -> str:
    base = make_slug(name)[:120] or "projet"
    slug, suffix = base, 2
    while Project.objects.filter(slug=slug).exists():
        slug, suffix = f"{base}-{suffix}", suffix + 1
    return slug


def _ensure_not_frozen(project: Project) -> None:
    if project.status in FROZEN_STATUSES:
        raise BusinessRuleViolation("Ce projet est archivé.", code="project_archived")


def _clean_texts(data: dict[str, Any]) -> dict[str, Any]:
    if "description" in data:
        data["description"] = sanitize_rich_text(data["description"])
    for field in ("name", "short_description", "problem", "objectives", "expected_availability"):
        if field in data:
            data[field] = to_plain_text(data[field])
    return data


def _notify_members(project: Project, *, actor: User, title: str) -> None:
    members = ProjectMember.objects.filter(
        project=project, status=ProjectMember.Status.ACTIVE
    ).select_related("user")
    for member in members:
        notify(
            member.user,
            type=Notification.Type.PROJECT_UPDATED,
            title=title,
            actor=actor,
            target=project,
            target_url=project_url(project),
        )


# --- Projets ---------------------------------------------------------------------


@transaction.atomic
def create_project(*, owner: User, data: dict[str, Any]) -> Project:
    """Crée le projet ; son créateur en devient propriétaire dans la même transaction."""
    data = _clean_texts(dict(data))
    technologies = data.pop("technologies", None)
    project = Project.objects.create(owner=owner, slug=_unique_slug(data["name"]), **data)
    if technologies:
        project.technologies.set(technologies)
    ProjectMember.objects.create(project=project, user=owner, role=Role.OWNER)
    return project


@transaction.atomic
def update_project(*, project: Project, actor: User, data: dict[str, Any]) -> Project:
    if not policies.can_edit_settings(project, actor):
        _forbid("Seul le propriétaire peut modifier les paramètres du projet.")
    project = Project.objects.select_for_update().get(pk=project.pk)
    data = _clean_texts(dict(data))
    technologies = data.pop("technologies", None)
    target_status = data.pop("status", project.status)
    if project.status in FROZEN_STATUSES and (data or technologies is not None):
        raise BusinessRuleViolation(
            "Désarchivez le projet avant de le modifier.", code="project_archived"
        )

    for field, value in data.items():
        setattr(project, field, value)
    status_changed = target_status != project.status
    if status_changed:
        ensure_transition(PROJECT_TRANSITIONS, project.status, target_status)
        project.status = target_status
        project.completed_at = timezone.now() if target_status == Project.Status.COMPLETED else None
    project.save()
    if technologies is not None:
        project.technologies.set(technologies)
    if status_changed:
        _notify_members(
            project,
            actor=actor,
            title=f"Le projet « {project.name} » est désormais : {project.get_status_display()}",
        )
    return project


def update_logo(*, project: Project, actor: User, upload: Any) -> Project:
    if not policies.can_edit_settings(project, actor):
        _forbid("Seul le propriétaire peut changer le logo.")
    return replace_image(project, "logo", upload, max_size=LOGO_SIZE)


def remove_logo(*, project: Project, actor: User) -> None:
    if not policies.can_edit_settings(project, actor):
        _forbid("Seul le propriétaire peut retirer le logo.")
    remove_image(project, "logo")


# --- Rôles recherchés --------------------------------------------------------------


def save_role_need(
    *, project: Project, actor: User, data: dict[str, Any], instance: ProjectRoleNeed | None = None
) -> ProjectRoleNeed:
    if not policies.can_manage_members(project, actor):
        _forbid("Seuls le propriétaire et les responsables habilités gèrent les rôles recherchés.")
    _ensure_not_frozen(project)
    data = dict(data)
    technologies = data.pop("required_technologies", None)
    if "description" in data:
        data["description"] = to_plain_text(data["description"])
    role_need = instance or ProjectRoleNeed(project=project)
    for field, value in data.items():
        setattr(role_need, field, value)
    role_need.save()
    if technologies is not None:
        role_need.required_technologies.set(technologies)
    return role_need


def delete_role_need(*, role_need: ProjectRoleNeed, actor: User) -> None:
    if not policies.can_manage_members(role_need.project, actor):
        _forbid("Seuls le propriétaire et les responsables habilités gèrent les rôles recherchés.")
    role_need.delete()


# --- Demandes pour rejoindre -------------------------------------------------------


def _ensure_joinable(project: Project) -> None:
    if project.status not in JOINABLE_STATUSES or not project.accepts_join_requests:
        raise BusinessRuleViolation(
            "Ce projet n'accepte pas de nouveaux membres.", code="project_closed"
        )


@transaction.atomic
def create_join_request(
    *, project: Project, user: User, message: str, requested_role: ProjectRoleNeed | None
) -> JoinRequest:
    """Demande motivée ; une seule active, et pas de relance immédiate après un refus."""
    project = Project.objects.select_for_update().get(pk=project.pk)
    _ensure_joinable(project)
    if policies.membership(project, user) is not None:
        raise BusinessRuleViolation("Vous êtes déjà membre de ce projet.", code="already_member")
    if requested_role is not None and (
        requested_role.project_id != project.pk or not requested_role.is_open
    ):
        raise exceptions.ValidationError({"requested_role": ["Ce rôle n'est pas ouvert."]})

    requests = JoinRequest.objects.filter(project=project, user=user)
    if requests.filter(status=JoinRequest.Status.PENDING).exists():
        raise BusinessRuleViolation(
            "Vous avez déjà une demande en attente pour ce projet.", code="duplicate_request"
        )
    last_rejection = (
        requests.filter(status=JoinRequest.Status.REJECTED).order_by("-reviewed_at").first()
    )
    if (
        last_rejection
        and not last_rejection.can_reapply
        and last_rejection.reviewed_at
        and timezone.now() - last_rejection.reviewed_at < REAPPLY_COOLDOWN
    ):
        raise BusinessRuleViolation(
            "Votre demande précédente a été refusée récemment ; patientez avant de redemander.",
            code="reapply_cooldown",
        )

    try:
        with transaction.atomic():
            join_request = JoinRequest.objects.create(
                project=project,
                user=user,
                message=to_plain_text(message),
                requested_role=requested_role,
            )
    except IntegrityError as exc:
        raise BusinessRuleViolation(
            "Vous avez déjà une demande en attente pour ce projet.", code="duplicate_request"
        ) from exc

    managers = ProjectMember.objects.filter(
        project=project, status=ProjectMember.Status.ACTIVE, role__in=MANAGER_ROLES
    ).select_related("user")
    for manager in managers:
        if manager.role == Role.OWNER or manager.can_manage_members:
            notify(
                manager.user,
                type=Notification.Type.JOIN_REQUEST_RECEIVED,
                title=f"{user.username} souhaite rejoindre « {project.name} »",
                actor=user,
                target=project,
                target_url=f"{project_url(project)}/demandes",
            )
    return join_request


def _lock_request(join_request: JoinRequest) -> tuple[JoinRequest, Project]:
    project = Project.objects.select_for_update().get(pk=join_request.project_id)
    join_request = JoinRequest.objects.select_for_update().get(pk=join_request.pk)
    return join_request, project


def _review(
    join_request: JoinRequest, project: Project, actor: User, target: str, response: str
) -> None:
    if not policies.can_manage_members(project, actor):
        _forbid("Seuls le propriétaire et les responsables habilités traitent les demandes.")
    ensure_transition(JOIN_REQUEST_TRANSITIONS, join_request.status, target)
    join_request.status = target
    join_request.reviewed_at = timezone.now()
    join_request.reviewed_by = actor
    join_request.response_message = to_plain_text(response)[:500]
    join_request.save()


@transaction.atomic
def accept_join_request(
    *, join_request: JoinRequest, actor: User, role: str = Role.CONTRIBUTOR, response: str = ""
) -> ProjectMember:
    """Acceptation et création du membre dans la même transaction, puis notification."""
    join_request, project = _lock_request(join_request)
    _ensure_joinable(project)
    if role == Role.OWNER:
        raise exceptions.ValidationError(
            {"role": ["Le rôle propriétaire ne s'attribue pas ainsi."]}
        )
    if role == Role.MANAGER and not policies.is_owner(project, actor):
        _forbid("Seul le propriétaire peut nommer un responsable.")
    _review(join_request, project, actor, JoinRequest.Status.ACCEPTED, response)
    if policies.membership(project, join_request.user) is not None:
        raise BusinessRuleViolation("Ce membre fait déjà partie du projet.", code="already_member")

    member = ProjectMember.objects.create(
        project=project,
        user=join_request.user,
        role=role,
        title=join_request.requested_role.role_name if join_request.requested_role else "",
    )
    need = join_request.requested_role
    if need is not None:
        filled = JoinRequest.objects.filter(
            requested_role=need, status=JoinRequest.Status.ACCEPTED
        ).count()
        if filled >= need.slots:
            need.is_open = False
            need.save(update_fields=["is_open", "updated_at"])
    notify(
        join_request.user,
        type=Notification.Type.JOIN_REQUEST_ACCEPTED,
        title=f"Bienvenue dans l'équipe de « {project.name} »",
        actor=actor,
        target=project,
        target_url=project_url(project),
    )
    return member


@transaction.atomic
def reject_join_request(
    *, join_request: JoinRequest, actor: User, response: str = ""
) -> JoinRequest:
    join_request, project = _lock_request(join_request)
    _review(join_request, project, actor, JoinRequest.Status.REJECTED, response)
    notify(
        join_request.user,
        type=Notification.Type.JOIN_REQUEST_REJECTED,
        title=f"Votre demande pour « {project.name} » n'a pas été retenue",
        actor=actor,
        target=project,
        target_url=project_url(project),
    )
    return join_request


@transaction.atomic
def withdraw_join_request(*, join_request: JoinRequest, actor: User) -> JoinRequest:
    join_request, _ = _lock_request(join_request)
    if join_request.user_id != actor.pk:
        _forbid("Seul le candidat peut retirer sa demande.")
    ensure_transition(JOIN_REQUEST_TRANSITIONS, join_request.status, JoinRequest.Status.WITHDRAWN)
    join_request.status = JoinRequest.Status.WITHDRAWN
    join_request.save(update_fields=["status", "updated_at"])
    return join_request


def allow_reapply(*, join_request: JoinRequest, actor: User) -> JoinRequest:
    if not policies.can_manage_members(join_request.project, actor):
        _forbid("Seuls le propriétaire et les responsables habilités traitent les demandes.")
    if join_request.status != JoinRequest.Status.REJECTED:
        raise BusinessRuleViolation(
            "Seule une demande refusée peut être rouverte.", code="invalid_transition"
        )
    join_request.can_reapply = True
    join_request.save(update_fields=["can_reapply", "updated_at"])
    return join_request


# --- Membres -----------------------------------------------------------------------


@transaction.atomic
def update_member(*, member: ProjectMember, actor: User, data: dict[str, Any]) -> ProjectMember:
    project = member.project
    _ensure_not_frozen(project)
    if not policies.can_manage_members(project, actor):
        _forbid("Seuls le propriétaire et les responsables habilités gèrent les membres.")
    if member.role == Role.OWNER:
        _forbid("Le rôle du propriétaire se change par un transfert de propriété.")
    owner_only = {"can_manage_members"} & data.keys() or data.get("role") in {Role.MANAGER}
    if (owner_only or member.role == Role.MANAGER) and not policies.is_owner(project, actor):
        _forbid("Seul le propriétaire gère les responsables et leurs droits.")
    if data.get("role") == Role.OWNER:
        raise exceptions.ValidationError({"role": ["Utilisez le transfert de propriété."]})
    for field, value in data.items():
        setattr(member, field, to_plain_text(value) if field == "title" else value)
    if member.role != Role.MANAGER:
        member.can_manage_members = False
    member.save()
    return member


def _end_membership(member: ProjectMember, status: str) -> None:
    member.status = status
    member.left_at = timezone.now()
    member.can_manage_members = False
    member.save(update_fields=["status", "left_at", "can_manage_members", "updated_at"])
    # Les tâches en cours sont libérées ; les tâches terminées gardent leur auteur.
    ProjectTask.objects.filter(project=member.project, assignee=member.user).exclude(
        status=ProjectTask.Status.DONE
    ).update(assignee=None)


@transaction.atomic
def remove_member(*, member: ProjectMember, actor: User) -> None:
    project = member.project
    if not policies.can_manage_members(project, actor):
        _forbid("Seuls le propriétaire et les responsables habilités gèrent les membres.")
    if member.role == Role.OWNER:
        _forbid("Le propriétaire ne peut pas être retiré.")
    if member.role == Role.MANAGER and not policies.is_owner(project, actor):
        _forbid("Seul le propriétaire peut retirer un responsable.")
    _end_membership(member, ProjectMember.Status.REMOVED)


@transaction.atomic
def leave_project(*, project: Project, user: User) -> None:
    member = policies.membership(project, user)
    if member is None:
        raise BusinessRuleViolation("Vous n'êtes pas membre de ce projet.", code="not_member")
    if member.role == Role.OWNER:
        raise BusinessRuleViolation(
            "Transférez la propriété avant de quitter le projet.", code="owner_cannot_leave"
        )
    _end_membership(member, ProjectMember.Status.LEFT)


@transaction.atomic
def transfer_ownership(*, project: Project, actor: User, new_owner: User) -> Project:
    project = Project.objects.select_for_update().get(pk=project.pk)
    if not policies.is_owner(project, actor):
        _forbid("Seul le propriétaire peut transférer la propriété.")
    target = policies.membership(project, new_owner)
    if target is None or target.role == Role.OBSERVER:
        raise BusinessRuleViolation(
            "Le nouveau propriétaire doit être un membre actif contributeur ou responsable.",
            code="invalid_new_owner",
        )
    current = policies.membership(project, actor)
    current.role, current.can_manage_members = Role.MANAGER, True
    current.save(update_fields=["role", "can_manage_members", "updated_at"])
    target.role, target.can_manage_members = Role.OWNER, False
    target.save(update_fields=["role", "can_manage_members", "updated_at"])
    project.owner = new_owner
    project.save(update_fields=["owner", "updated_at"])
    return project


# --- Tâches ------------------------------------------------------------------------


def _validate_assignee(project: Project, actor: User, assignee: User | None) -> None:
    if assignee is None:
        return
    member = policies.membership(project, assignee)
    if member is None:
        raise BusinessRuleViolation(
            "Une tâche ne peut être assignée qu'à un membre actif du projet.",
            code="assignee_not_member",
        )
    if member.role == Role.OBSERVER:
        raise BusinessRuleViolation(
            "Un observateur ne peut pas recevoir de tâche.", code="assignee_observer"
        )
    if not policies.can_manage_tasks(project, actor) and assignee.pk != actor.pk:
        _forbid("Un contributeur ne peut s'assigner que lui-même.")


def _notify_assignee(task: ProjectTask, actor: User) -> None:
    if task.assignee is None:
        return
    notify(
        task.assignee,
        type=Notification.Type.TASK_ASSIGNED,
        title=f"Nouvelle tâche dans « {task.project.name} » : {task.title}",
        actor=actor,
        target=task.project,
        target_url=f"{project_url(task.project)}/taches",
    )


@transaction.atomic
def create_task(*, project: Project, actor: User, data: dict[str, Any]) -> ProjectTask:
    if not policies.can_contribute(project, actor):
        _forbid("Seuls les propriétaires, responsables et contributeurs créent des tâches.")
    _ensure_not_frozen(project)
    data = dict(data)
    _validate_assignee(project, actor, data.get("assignee"))
    if data.get("status", ProjectTask.Status.TODO) == ProjectTask.Status.DONE:
        data["completed_at"] = timezone.now()
    data["title"] = to_plain_text(data["title"])
    data["description"] = to_plain_text(data.get("description", ""))
    task = ProjectTask.objects.create(project=project, created_by=actor, **data)
    _notify_assignee(task, actor)
    return task


@transaction.atomic
def update_task(*, task: ProjectTask, actor: User, data: dict[str, Any]) -> ProjectTask:
    task = ProjectTask.objects.select_for_update().select_related("project").get(pk=task.pk)
    project = task.project
    _ensure_not_frozen(project)
    if not policies.can_edit_task(task, actor):
        _forbid("Vous ne pouvez pas modifier cette tâche.")
    manager = policies.can_manage_tasks(project, actor)
    data = dict(data)

    assignee_changed = "assignee" in data and data["assignee"] != task.assignee
    if assignee_changed:
        _validate_assignee(project, actor, data["assignee"])
        if not manager and task.assignee_id not in {None, actor.pk}:
            _forbid("Seuls le propriétaire et les responsables réaffectent une tâche.")

    target = data.pop("status", task.status)
    if target != task.status:
        ensure_transition(TASK_TRANSITIONS, task.status, target)
        is_assignee = (data.get("assignee", task.assignee) or None) == actor
        if target == ProjectTask.Status.DONE and not (manager or is_assignee):
            _forbid(
                "Seuls la personne assignée, le propriétaire ou un responsable terminent une tâche."
            )
        if task.status == ProjectTask.Status.DONE and not manager:
            _forbid("Seuls le propriétaire et les responsables rouvrent une tâche terminée.")
        task.status = target
        task.completed_at = timezone.now() if target == ProjectTask.Status.DONE else None

    for field in ("title", "description"):
        if field in data:
            data[field] = to_plain_text(data[field])
    for field, value in data.items():
        setattr(task, field, value)
    task.save()
    if assignee_changed:
        _notify_assignee(task, actor)
    return task


def delete_task(*, task: ProjectTask, actor: User) -> None:
    """Suppression réservée aux gestionnaires ; le travail terminé d'autrui est conservé."""
    if not policies.can_manage_tasks(task.project, actor):
        _forbid("Seuls le propriétaire et les responsables suppriment une tâche.")
    if task.status == ProjectTask.Status.DONE:
        raise BusinessRuleViolation(
            "Une tâche terminée conserve son historique et ne peut pas être supprimée.",
            code="task_done",
        )
    task.delete()
