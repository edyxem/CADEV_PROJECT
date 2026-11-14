"""Traitement des signalements et actions de modération, toujours journalisées."""

from datetime import timedelta
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import Model
from django.utils import timezone
from rest_framework import exceptions

from apps.accounts.models import User
from apps.accounts.tokens import revoke_all_sessions
from apps.community import services as community_services
from apps.community.models import Answer, Comment, ContentStatus, Post
from apps.notifications.models import Notification
from apps.notifications.services import notify
from common.exceptions import BusinessRuleViolation
from common.permissions import is_admin, is_moderator
from common.sanitization import to_plain_text
from common.transitions import ensure_transition

from . import targets
from .models import REPORT_TRANSITIONS, AuditLog, ModerationAction, Report, TargetType

Action = ModerationAction.ActionType
MAX_SUSPENSION_DAYS = 90
# Ces actions règlent aussi les autres signalements ouverts sur la même cible.
RESOLVING_ACTIONS = {Action.HIDE, Action.DELETE, Action.SUSPEND, Action.BAN}
ADMIN_ONLY_ACTIONS = {Action.BAN, Action.UNBAN}
CONTENT_TARGET_STATUS = {
    Action.HIDE: ContentStatus.HIDDEN,
    Action.RESTORE: ContentStatus.PUBLISHED,
    Action.DELETE: ContentStatus.DELETED,
}
NOTIFICATION_TITLES = {
    Action.WARNING: "Avertissement de la modération",
    Action.HIDE: "Un de vos contenus a été masqué par la modération",
    Action.RESTORE: "Un de vos contenus a été restauré",
    Action.DELETE: "Un de vos contenus a été retiré par la modération",
    Action.SUSPEND: "Votre compte a été suspendu temporairement",
    Action.UNSUSPEND: "La suspension de votre compte a été levée",
    Action.BAN: "Votre compte a été banni",
    Action.UNBAN: "Le bannissement de votre compte a été levé",
}


def audit(
    actor: User | None, action: str, *, target_type: str = "", target_id: Any = "", **metadata: Any
) -> AuditLog:
    """Ajoute une entrée au journal d'audit. Ne jamais y placer de secret ou de mot de passe."""
    return AuditLog.objects.create(
        actor=actor,
        action=action,
        target_type=target_type,
        target_id=str(target_id or ""),
        metadata={key: value for key, value in metadata.items() if value not in (None, "")},
    )


def _ensure_moderator(user: User) -> None:
    if not is_moderator(user):
        raise exceptions.PermissionDenied("Action réservée à la modération.")


def load_target(target_type: str, target_id: Any) -> tuple[targets.TargetSpec, Model]:
    spec = targets.get_spec(target_type)
    target = spec.loader(target_id) if spec else None
    if spec is None or target is None:
        raise exceptions.NotFound("Cible introuvable.")
    return spec, target


# --- Signalements ------------------------------------------------------------------


@transaction.atomic
def create_report(
    *, reporter: User, target_type: str, target_id: Any, reason: str, details: str = ""
) -> Report:
    spec, target = load_target(target_type, target_id)
    if not spec.visible_to(target, reporter):
        raise exceptions.NotFound("Cible introuvable.")
    author = spec.author(target)
    if author is not None and author.pk == reporter.pk:
        raise BusinessRuleViolation(
            "Vous ne pouvez pas signaler votre propre contenu.", code="self_report"
        )
    try:
        with transaction.atomic():
            return Report.objects.create(
                reporter=reporter,
                target_type=target_type,
                target_id=target.pk,
                reason=reason,
                details=to_plain_text(details),
            )
    except IntegrityError as exc:
        raise BusinessRuleViolation(
            "Vous avez déjà signalé ce contenu ; il est en cours de traitement.",
            code="duplicate_report",
        ) from exc


def _ensure_can_handle(report: Report, moderator: User) -> None:
    _ensure_moderator(moderator)
    if report.reporter_id == moderator.pk:
        raise exceptions.PermissionDenied("Vous ne pouvez pas traiter vos propres signalements.")


@transaction.atomic
def claim_report(*, report: Report, moderator: User) -> Report:
    report = Report.objects.select_for_update().get(pk=report.pk)
    _ensure_can_handle(report, moderator)
    if report.status == Report.Status.REVIEWING and report.assigned_to_id not in {
        None,
        moderator.pk,
    }:
        raise BusinessRuleViolation(
            "Ce signalement est déjà examiné par un autre modérateur.", code="already_claimed"
        )
    if report.status != Report.Status.REVIEWING:
        ensure_transition(REPORT_TRANSITIONS, report.status, Report.Status.REVIEWING)
    report.status, report.assigned_to = Report.Status.REVIEWING, moderator
    report.save(update_fields=["status", "assigned_to", "updated_at"])
    audit(moderator, "report.claim", target_type="report", target_id=report.pk)
    return report


@transaction.atomic
def close_report(*, report: Report, moderator: User) -> Report:
    report = Report.objects.select_for_update().get(pk=report.pk)
    _ensure_can_handle(report, moderator)
    ensure_transition(REPORT_TRANSITIONS, report.status, Report.Status.CLOSED)
    report.status = Report.Status.CLOSED
    report.save(update_fields=["status", "updated_at"])
    audit(moderator, "report.close", target_type="report", target_id=report.pk)
    return report


def _resolve(report: Report, moderator: User, status: str, note: str) -> None:
    ensure_transition(REPORT_TRANSITIONS, report.status, status)
    report.status = status
    report.resolved_at = timezone.now()
    report.resolution_note = note[:500]
    report.assigned_to = report.assigned_to or moderator
    report.save(
        update_fields=["status", "resolved_at", "resolution_note", "assigned_to", "updated_at"]
    )


# --- Actions ----------------------------------------------------------------------


def _account_for(spec: targets.TargetSpec, target: Model) -> User:
    account = spec.author(target)
    if account is None:  # pragma: no cover - toutes les cibles P0 ont un auteur
        raise BusinessRuleViolation("Cette cible n'est liée à aucun compte.", code="no_account")
    return account


def _ensure_can_sanction(moderator: User, account: User) -> None:
    if account.is_admin:
        raise exceptions.PermissionDenied(
            "Un compte administrateur ne peut pas être sanctionné ici."
        )
    if account.is_moderator and not is_admin(moderator):
        raise exceptions.PermissionDenied("Seul un administrateur peut sanctionner un modérateur.")


def _apply_account_action(
    action: str, moderator: User, account: User, days: int | None
) -> tuple[str, str, Any]:
    previous = targets.account_state(account)
    expires_at = None
    if action in {Action.SUSPEND, Action.BAN}:
        _ensure_can_sanction(moderator, account)
    if action == Action.SUSPEND:
        if account.is_banned:
            raise BusinessRuleViolation("Ce compte est déjà banni.", code="already_banned")
        expires_at = timezone.now() + timedelta(days=days or 1)
        account.is_active, account.suspended_until = False, expires_at
    elif action == Action.UNSUSPEND:
        if not account.is_suspended:
            raise BusinessRuleViolation("Ce compte n'est pas suspendu.", code="not_suspended")
        account.is_active, account.suspended_until = not account.is_banned, None
    elif action == Action.BAN:
        account.is_active, account.banned_at, account.suspended_until = False, timezone.now(), None
    elif action == Action.UNBAN:
        if not account.is_banned:
            raise BusinessRuleViolation("Ce compte n'est pas banni.", code="not_banned")
        account.is_active, account.banned_at = True, None
    account.save(update_fields=["is_active", "suspended_until", "banned_at"])
    if not account.is_active:
        revoke_all_sessions(account)
    return previous, targets.account_state(account), expires_at


def _apply_content_action(
    action: str, moderator: User, spec: targets.TargetSpec, target: Model
) -> tuple[str, str]:
    if isinstance(target, Post | Comment | Answer):
        previous = community_services.moderate_status(
            target, target=CONTENT_TARGET_STATUS[action], actor=moderator
        )
        return previous, target.status
    if spec.hide is not None and action in {Action.HIDE, Action.RESTORE}:
        return spec.hide(target, action == Action.HIDE)
    raise BusinessRuleViolation("Action impossible sur cette cible.", code="unsupported_action")


@transaction.atomic
def take_action(
    *,
    moderator: User,
    action: str,
    reason: str,
    report: Report | None = None,
    target_type: str | None = None,
    target_id: Any = None,
    duration_days: int | None = None,
) -> ModerationAction:
    """Applique une décision et la journalise ; notifie le membre concerné.

    - un modérateur ne traite ni ses propres signalements ni ses propres contenus ;
    - le bannissement et sa levée sont réservés aux administrateurs ;
    - restaurer un contenu supprimé est réservé aux administrateurs.
    """
    _ensure_moderator(moderator)
    reason = to_plain_text(reason)
    if report is not None:
        report = Report.objects.select_for_update().get(pk=report.pk)
        _ensure_can_handle(report, moderator)
        if report.status not in Report.OPEN_STATUSES:
            raise BusinessRuleViolation("Ce signalement est déjà traité.", code="report_closed")
        target_type, target_id = report.target_type, report.target_id

    spec, target = load_target(target_type, target_id)
    account = _account_for(spec, target)
    if account.pk == moderator.pk:
        raise exceptions.PermissionDenied(
            "Vous ne pouvez pas modérer vos propres contenus ou votre compte."
        )
    if action in ADMIN_ONLY_ACTIONS and not is_admin(moderator):
        raise exceptions.PermissionDenied("Le bannissement relève d'une décision administrative.")
    if action == Action.NO_ACTION:
        if report is None:
            raise BusinessRuleViolation(
                "« Aucune action » s'applique à un signalement.", code="report_required"
            )
    elif action not in spec.actions:
        raise BusinessRuleViolation(
            "Action impossible sur ce type de cible.", code="unsupported_action"
        )

    previous = new = ""
    expires_at = None
    if action in CONTENT_TARGET_STATUS:
        previous, new = _apply_content_action(action, moderator, spec, target)
    elif action in {Action.SUSPEND, Action.UNSUSPEND, Action.BAN, Action.UNBAN}:
        previous, new, expires_at = _apply_account_action(action, moderator, account, duration_days)

    record = ModerationAction.objects.create(
        report=report,
        moderator=moderator,
        target_type=target_type,
        target_id=target.pk,
        action_type=action,
        reason=reason,
        previous_state=previous,
        new_state=new,
        expires_at=expires_at,
    )
    audit(
        moderator,
        f"moderation.{action.lower()}",
        target_type=target_type,
        target_id=target.pk,
        report=str(report.pk) if report else None,
        previous_state=previous,
        new_state=new,
        reason=reason,
    )

    if report is not None:
        status = (
            Report.Status.REJECTED if action == Action.NO_ACTION else Report.Status.ACTION_TAKEN
        )
        _resolve(report, moderator, status, reason)
        if action in RESOLVING_ACTIONS:
            others = (
                Report.objects.select_for_update()
                .filter(
                    target_type=target_type, target_id=target.pk, status__in=Report.OPEN_STATUSES
                )
                .exclude(pk=report.pk)
            )
            for other in others:
                _resolve(other, moderator, Report.Status.ACTION_TAKEN, reason)

    if action in NOTIFICATION_TITLES:
        notify(
            account,
            type=Notification.Type.MODERATION_ACTION,
            title=NOTIFICATION_TITLES[action],
            message=f"Motif : {reason}"[:300],
            target_url=spec.preview(target).get("url", ""),
            include_inactive=True,
        )
    return record


def moderate_from_admin(obj: Model, *, target: str, actor: User) -> bool:
    """Masque ou restaure depuis Django Admin en passant par le même chemin journalisé."""
    target_type = {
        Post: TargetType.POST,
        Comment: TargetType.COMMENT,
        Answer: TargetType.ANSWER,
    }[type(obj)]
    action = Action.HIDE if target == ContentStatus.HIDDEN else Action.RESTORE
    try:
        take_action(
            moderator=actor,
            action=action,
            reason="Action effectuée depuis l'administration.",
            target_type=target_type,
            target_id=obj.pk,
        )
    except (exceptions.APIException, BusinessRuleViolation):
        return False
    return True
