"""Règles des communautés : au moins un responsable, publication réservée aux membres."""

from typing import Any

from django.db import IntegrityError, transaction
from rest_framework import exceptions

from apps.accounts.models import User
from apps.catalog.normalization import make_slug
from apps.community.models import Post
from apps.moderation.services import audit
from apps.notifications.models import Notification
from apps.notifications.services import notify
from common.exceptions import BusinessRuleViolation
from common.sanitization import to_plain_text

from .models import Community, CommunityMembership

Role, Status = CommunityMembership.Role, CommunityMembership.Status


def membership(community: Community, user: Any) -> CommunityMembership | None:
    if user is None or not user.is_authenticated:
        return None
    return CommunityMembership.objects.filter(
        community=community, user=user, status=Status.ACTIVE
    ).first()


def is_leader(community: Community, user: Any) -> bool:
    member = membership(community, user)
    return member is not None and member.role == Role.LEADER


def ensure_can_publish(community: Community, user: User) -> None:
    """Appelé par ``community.services`` avant de publier dans une communauté."""
    if community.hidden_by_moderation or membership(community, user) is None:
        raise exceptions.PermissionDenied("Rejoignez la communauté pour y publier.")


@transaction.atomic
def create_community(*, creator: User, data: dict[str, Any]) -> Community:
    data = dict(data)
    for field in ("name", "description", "rules", "city"):
        if field in data:
            data[field] = to_plain_text(data[field])
    base = make_slug(data["name"])[:120] or "communaute"
    slug, suffix = base, 2
    while Community.objects.filter(slug=slug).exists():
        slug, suffix = f"{base}-{suffix}", suffix + 1
    community = Community.objects.create(created_by=creator, slug=slug, **data)
    CommunityMembership.objects.create(community=community, user=creator, role=Role.LEADER)
    return community


def update_community(*, community: Community, actor: User, data: dict[str, Any]) -> Community:
    if not is_leader(community, actor):
        raise exceptions.PermissionDenied("Réservé aux responsables de la communauté.")
    for field, value in data.items():
        setattr(community, field, to_plain_text(value) if isinstance(value, str) else value)
    community.save()
    return community


@transaction.atomic
def join(*, community: Community, user: User) -> CommunityMembership:
    if community.hidden_by_moderation:
        raise exceptions.NotFound()
    existing = CommunityMembership.objects.filter(
        community=community, user=user, status__in=[Status.ACTIVE, Status.BANNED]
    ).first()
    if existing is not None:
        code = "banned" if existing.status == Status.BANNED else "already_member"
        raise BusinessRuleViolation("Adhésion impossible.", code=code)
    try:
        with transaction.atomic():
            return CommunityMembership.objects.create(community=community, user=user)
    except IntegrityError as exc:  # pragma: no cover - concurrence
        raise BusinessRuleViolation("Adhésion impossible.", code="already_member") from exc


def _active_leaders(community: Community) -> int:
    return CommunityMembership.objects.filter(
        community=community, status=Status.ACTIVE, role=Role.LEADER
    ).count()


@transaction.atomic
def leave(*, community: Community, user: User) -> None:
    member = membership(community, user)
    if member is None:
        raise BusinessRuleViolation("Vous n'êtes pas membre.", code="not_member")
    if member.role == Role.LEADER and _active_leaders(community) <= 1:
        raise BusinessRuleViolation(
            "Désignez un autre responsable avant de partir.", code="last_leader"
        )
    member.status = Status.LEFT
    member.save(update_fields=["status", "updated_at"])


@transaction.atomic
def manage_member(
    *, member: CommunityMembership, actor: User, role: str | None = None, ban: bool = False
) -> CommunityMembership:
    community = member.community
    if not is_leader(community, actor):
        raise exceptions.PermissionDenied("Réservé aux responsables de la communauté.")
    if member.user_id == actor.pk:
        raise BusinessRuleViolation(
            "Utilisez « quitter » pour votre propre adhésion.", code="self_management"
        )
    demoting_leader = member.role == Role.LEADER and (ban or role == Role.MEMBER)
    if (
        demoting_leader and _active_leaders(community) <= 1
    ):  # pragma: no cover - l'acteur est lui-même responsable
        raise BusinessRuleViolation("La communauté doit garder un responsable.", code="last_leader")
    if ban:
        member.status = Status.BANNED
        audit(
            actor,
            "community.ban",
            target_type="community",
            target_id=community.pk,
            user=member.user.username,
        )
    if role:
        member.role = role
    member.save(update_fields=["status", "role", "updated_at"])
    return member


def set_post_visibility(
    *, community: Community, post: Post, actor: User, hidden: bool, reason: str
) -> Post:
    """Modération locale : retire une publication du fil de la communauté (journalisé)."""
    if not is_leader(community, actor):
        raise exceptions.PermissionDenied("Réservé aux responsables de la communauté.")
    if post.community_id != community.pk:
        raise exceptions.NotFound()
    post.community_hidden = hidden
    post.save(update_fields=["community_hidden", "updated_at"])
    audit(
        actor,
        "community.post_hide" if hidden else "community.post_restore",
        target_type="post",
        target_id=post.pk,
        community=str(community.pk),
        reason=to_plain_text(reason),
    )
    if hidden:
        notify(
            post.author,
            type=Notification.Type.MODERATION_ACTION,
            title=f"Votre publication a été retirée de la communauté « {community.name} »",
            message=f"Motif : {to_plain_text(reason)}"[:300],
            actor=actor,
            target_url=f"/publications/{post.pk}",
        )
    return post
