"""Règles du mentorat : volontaire, explicite, jamais accepté automatiquement."""

from typing import Any

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import exceptions

from apps.accounts.models import User
from apps.notifications.models import Notification
from apps.notifications.services import notify
from common.exceptions import BusinessRuleViolation
from common.sanitization import to_plain_text
from common.transitions import ensure_transition

from .models import (
    MENTORSHIP_TRANSITIONS,
    SESSION_TRANSITIONS,
    MentorProfile,
    MentorshipFeedback,
    MentorshipRequest,
    MentorshipSession,
)

Status = MentorshipRequest.Status
URL = "/mentorat"


def _notify(recipient: User, actor: User, title: str) -> None:
    notify(
        recipient,
        type=Notification.Type.MENTORSHIP_UPDATE,
        title=title,
        actor=actor,
        target_url=URL,
    )


def is_participant(request: MentorshipRequest, user: User) -> bool:
    return user.pk in {request.mentee_id, request.mentor.user_id}


@transaction.atomic
def save_mentor_profile(*, user: User, data: dict[str, Any]) -> MentorProfile:
    data = dict(data)
    domains, technologies = data.pop("domains", None), data.pop("technologies", None)
    for field in ("headline", "bio"):
        if field in data:
            data[field] = to_plain_text(data[field])
    profile, _ = MentorProfile.objects.update_or_create(user=user, defaults=data)
    if domains is not None:
        profile.domains.set(domains)
    if technologies is not None:
        profile.technologies.set(technologies)
    return profile


@transaction.atomic
def request_mentorship(*, mentee: User, mentor: MentorProfile, goal: str) -> MentorshipRequest:
    if mentor.user_id == mentee.pk:
        raise BusinessRuleViolation(
            "Vous ne pouvez pas être votre propre mentor.", code="self_mentorship"
        )
    if not mentor.is_available or not mentor.user.is_active:
        raise BusinessRuleViolation(
            "Ce mentor n'accepte pas de demande actuellement.", code="mentor_unavailable"
        )
    try:
        with transaction.atomic():
            request = MentorshipRequest.objects.create(
                mentee=mentee, mentor=mentor, goal=to_plain_text(goal)
            )
    except IntegrityError as exc:
        raise BusinessRuleViolation(
            "Une demande est déjà en cours avec ce mentor.", code="duplicate_request"
        ) from exc
    _notify(mentor.user, mentee, f"{mentee.username} souhaite être accompagné·e par vous")
    return request


def _transition(request: MentorshipRequest, target: str) -> MentorshipRequest:
    ensure_transition(MENTORSHIP_TRANSITIONS, request.status, target)
    request.status = target
    if target in {Status.ACCEPTED, Status.DECLINED}:
        request.responded_at = timezone.now()
    if target == Status.COMPLETED:
        request.completed_at = timezone.now()
    request.save()
    return request


@transaction.atomic
def respond(
    *, request: MentorshipRequest, mentor_user: User, accept: bool, message: str = ""
) -> MentorshipRequest:
    request = (
        MentorshipRequest.objects.select_for_update().select_related("mentor").get(pk=request.pk)
    )
    if request.mentor.user_id != mentor_user.pk:
        raise exceptions.PermissionDenied("Seul le mentor sollicité répond à la demande.")
    if accept:
        active = MentorshipRequest.objects.filter(
            mentor=request.mentor, status=Status.ACCEPTED
        ).count()
        if active >= request.mentor.max_active_mentees:
            raise BusinessRuleViolation("Capacité d'accompagnement atteinte.", code="mentor_full")
    request.response_message = to_plain_text(message)[:500]
    _transition(request, Status.ACCEPTED if accept else Status.DECLINED)
    _notify(
        request.mentee,
        mentor_user,
        f"Votre demande de mentorat a été {'acceptée' if accept else 'déclinée'}",
    )
    return request


def cancel(*, request: MentorshipRequest, actor: User) -> MentorshipRequest:
    if not is_participant(request, actor):
        raise exceptions.PermissionDenied("Réservé aux participants.")
    _transition(request, Status.CANCELLED)
    other = request.mentor.user if actor.pk == request.mentee_id else request.mentee
    _notify(other, actor, "Un mentorat a été annulé")
    return request


def complete(*, request: MentorshipRequest, actor: User) -> MentorshipRequest:
    if not is_participant(request, actor):
        raise exceptions.PermissionDenied("Réservé aux participants.")
    return _transition(request, Status.COMPLETED)


def plan_session(
    *, request: MentorshipRequest, actor: User, data: dict[str, Any]
) -> MentorshipSession:
    if not is_participant(request, actor):
        raise exceptions.PermissionDenied("Réservé aux participants.")
    if request.status != Status.ACCEPTED:
        raise BusinessRuleViolation(
            "Le mentorat doit être accepté et en cours.", code="mentorship_not_active"
        )
    data = dict(data)
    for field in ("agenda", "notes"):
        if field in data:
            data[field] = to_plain_text(data[field])
    session = MentorshipSession.objects.create(request=request, **data)
    other = request.mentor.user if actor.pk == request.mentee_id else request.mentee
    _notify(other, actor, "Nouvelle session de mentorat planifiée")
    return session


def update_session(
    *, session: MentorshipSession, actor: User, data: dict[str, Any]
) -> MentorshipSession:
    if not is_participant(session.request, actor):
        raise exceptions.PermissionDenied("Réservé aux participants.")
    data = dict(data)
    target = data.pop("status", session.status)
    if target != session.status:
        ensure_transition(SESSION_TRANSITIONS, session.status, target)
        session.status = target
    for field, value in data.items():
        setattr(session, field, to_plain_text(value) if field in {"agenda", "notes"} else value)
    session.save()
    return session


def leave_feedback(
    *, session: MentorshipSession, author: User, rating: int, comment: str = ""
) -> MentorshipFeedback:
    if not is_participant(session.request, author):
        raise exceptions.PermissionDenied("Réservé aux participants.")
    if session.status != MentorshipSession.Status.COMPLETED:
        raise BusinessRuleViolation(
            "Un retour se donne après une session terminée.", code="session_not_completed"
        )
    try:
        with transaction.atomic():
            return MentorshipFeedback.objects.create(
                session=session, author=author, rating=rating, comment=to_plain_text(comment)
            )
    except IntegrityError as exc:
        raise BusinessRuleViolation(
            "Vous avez déjà laissé un retour.", code="duplicate_feedback"
        ) from exc
