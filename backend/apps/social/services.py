"""Règles des abonnements et du fil personnalisé."""

from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import Q, QuerySet

from apps.accounts.models import User
from apps.community import selectors as community_selectors
from apps.community.models import Post
from apps.notifications.models import Notification
from apps.notifications.services import notify
from common.exceptions import BusinessRuleViolation

from .models import Follow

MAX_FOLLOWS = 500
TARGET_FIELD = {
    Follow.TargetType.USER: "followed_user",
    Follow.TargetType.TECHNOLOGY: "technology",
    Follow.TargetType.CATEGORY: "category",
}


@transaction.atomic
def follow(*, follower: User, target_type: str, target: Any) -> Follow:
    if target_type == Follow.TargetType.USER:
        if target.pk == follower.pk:
            raise BusinessRuleViolation(
                "Vous ne pouvez pas vous suivre vous-même.", code="self_follow"
            )
        if not target.is_active:
            raise BusinessRuleViolation("Ce compte n'est plus actif.", code="inactive_account")
    if Follow.objects.filter(follower=follower).count() >= MAX_FOLLOWS:
        raise BusinessRuleViolation(f"Maximum {MAX_FOLLOWS} abonnements.", code="follow_limit")
    try:
        with transaction.atomic():
            subscription = Follow.objects.create(
                follower=follower, target_type=target_type, **{TARGET_FIELD[target_type]: target}
            )
    except IntegrityError as exc:
        raise BusinessRuleViolation(
            "Vous suivez déjà cet élément.", code="already_following"
        ) from exc

    if target_type == Follow.TargetType.USER:
        notify(
            target,
            type=Notification.Type.NEW_FOLLOWER,
            title=f"{follower.username} suit désormais votre activité",
            actor=follower,
            target_url=f"/membres/{follower.username}",
        )
    return subscription


def personal_feed(user: User) -> QuerySet[Post]:
    """Publications des membres, technologies et catégories suivis.

    Complète le fil général sans jamais le remplacer (§K) : rien n'est masqué
    du fil communautaire.
    """
    follows = Follow.objects.filter(follower=user)
    condition = (
        Q(author__in=follows.filter(target_type=Follow.TargetType.USER).values("followed_user"))
        | Q(
            technologies__in=follows.filter(target_type=Follow.TargetType.TECHNOLOGY).values(
                "technology"
            )
        )
        | Q(category__in=follows.filter(target_type=Follow.TargetType.CATEGORY).values("category"))
    )
    matching = Post.all_objects.filter(condition).exclude(author=user).values("pk")
    return community_selectors.feed(user).filter(pk__in=matching).order_by("-published_at")
