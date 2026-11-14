"""Calcul déterministe et recalculable de la réputation à partir des données sources."""

from collections import Counter, defaultdict
from collections.abc import Iterable
from typing import Any

from django.apps import apps
from django.db import transaction
from django.db.models import Sum

from apps.accounts.models import User
from apps.community.models import Answer, AnswerVote, ContentStatus, Post, PostVote
from apps.notifications.models import Notification
from apps.notifications.services import notify
from apps.projects.models import Project, ProjectMember, ProjectTask
from common.exceptions import BusinessRuleViolation
from common.sanitization import to_plain_text

from .models import Achievement, ContributionEvent, EventType, Recommendation, UserAchievement
from .rules import RULES

Key = tuple[str, Any]  # (type d'événement, identifiant de l'objet source)


def _capped(rows: Iterable[tuple[Any, Any]], max_per_object: int | None) -> list[Any]:
    """``rows`` = (identifiant de l'objet, identifiant de l'événement) triés par ancienneté."""
    kept, per_object = [], Counter()
    for object_id, event_id in rows:
        per_object[object_id] += 1
        if max_per_object is None or per_object[object_id] <= max_per_object:
            kept.append(event_id)
    return kept


def _desired_events(user: User) -> dict[Key, tuple[str, int]]:
    """Événements que les données actuelles justifient : {(type, objet): (type d'objet, points)}."""
    published = ContentStatus.PUBLISHED
    sources: dict[str, tuple[str, list[Any]]] = {}

    sources[EventType.ANSWER_ACCEPTED] = (
        "answer",
        list(
            Answer.all_objects.filter(
                author=user, is_accepted=True, status=published, question__status=published
            ).values_list("pk", flat=True)
        ),
    )
    answer_votes = AnswerVote.objects.filter(
        answer__author=user,
        answer__status=published,
        answer__question__status=published,
        user__is_active=True,
    ).order_by("created_at")
    sources[EventType.ANSWER_UPVOTED] = (
        "answervote",
        _capped(
            answer_votes.values_list("answer_id", "pk"),
            RULES[EventType.ANSWER_UPVOTED].max_per_object,
        ),
    )
    post_votes = PostVote.objects.filter(
        post__author=user, post__status=published, user__is_active=True
    ).order_by("created_at")
    sources[EventType.POST_UPVOTED] = (
        "postvote",
        _capped(
            post_votes.values_list("post_id", "pk"), RULES[EventType.POST_UPVOTED].max_per_object
        ),
    )
    sources[EventType.ARTICLE_PUBLISHED] = (
        "post",
        list(
            Post.all_objects.filter(author=user, type=Post.Type.ARTICLE, status=published)
            .order_by("published_at")
            .values_list("pk", flat=True)
        ),
    )
    sources[EventType.TASK_COMPLETED] = (
        "projecttask",
        list(
            ProjectTask.objects.filter(assignee=user, status=ProjectTask.Status.DONE)
            .order_by("completed_at")
            .values_list("pk", flat=True)
        ),
    )
    sources[EventType.PROJECT_COMPLETED] = (
        "project",
        list(
            Project.objects.filter(
                status=Project.Status.COMPLETED,
                hidden_by_moderation=False,
                memberships__user=user,
                memberships__status=ProjectMember.Status.ACTIVE,
            ).values_list("pk", flat=True)
        ),
    )
    sources[EventType.RECOMMENDATION_RECEIVED] = (
        "recommendation",
        list(
            Recommendation.objects.filter(recommended=user, recommender__is_active=True)
            .order_by("created_at")
            .values_list("pk", flat=True)
        ),
    )
    if apps.is_installed("apps.mentorship"):
        from apps.mentorship.models import MentorshipRequest

        sources[EventType.MENTORSHIP_COMPLETED] = (
            "mentorshiprequest",
            list(
                MentorshipRequest.objects.filter(
                    mentor__user=user, status=MentorshipRequest.Status.COMPLETED
                )
                .order_by("updated_at")
                .values_list("pk", flat=True)
            ),
        )

    desired: dict[Key, tuple[str, int]] = {}
    for event_type, (object_type, object_ids) in sources.items():
        rule = RULES[event_type]
        if rule.max_total is not None:
            object_ids = object_ids[: rule.max_total]
        for object_id in object_ids:
            desired[(event_type, object_id)] = (object_type, rule.points)
    return desired


@transaction.atomic
def sync_user(user: User) -> int:
    """Aligne les événements stockés sur les données réelles, puis les badges ; renvoie le score."""
    desired = _desired_events(user)
    existing = {
        (event.event_type, event.object_id): event
        for event in ContributionEvent.objects.select_for_update().filter(user=user)
    }
    stale = [event.pk for key, event in existing.items() if key not in desired]
    ContributionEvent.objects.filter(pk__in=stale).delete()
    ContributionEvent.objects.bulk_create(
        [
            ContributionEvent(
                user=user,
                event_type=event_type,
                object_type=object_type,
                object_id=object_id,
                points=points,
            )
            for (event_type, object_id), (object_type, points) in desired.items()
            if (event_type, object_id) not in existing
        ],
        ignore_conflicts=True,
    )
    _sync_achievements(user)
    return score_of(user)


def _sync_achievements(user: User) -> None:
    counts = Counter(
        ContributionEvent.objects.filter(user=user).values_list("event_type", flat=True)
    )
    earned = {
        achievement.pk: achievement
        for achievement in Achievement.objects.filter(is_active=True)
        if counts[achievement.event_type] >= achievement.threshold
    }
    held = set(UserAchievement.objects.filter(user=user).values_list("achievement_id", flat=True))
    UserAchievement.objects.filter(user=user).exclude(achievement_id__in=earned).delete()
    for achievement_id, achievement in earned.items():
        if achievement_id in held:
            continue
        UserAchievement.objects.create(user=user, achievement=achievement)
        notify(
            user,
            type=Notification.Type.ACHIEVEMENT_AWARDED,
            title=f"Nouveau badge : {achievement.name}",
            message=achievement.description,
            target_url=f"/membres/{user.username}",
        )


def score_of(user: User) -> int:
    return ContributionEvent.objects.filter(user=user).aggregate(total=Sum("points"))["total"] or 0


def breakdown(user: User) -> list[dict[str, Any]]:
    totals: dict[str, dict[str, int]] = defaultdict(lambda: {"count": 0, "points": 0})
    for event_type, points in ContributionEvent.objects.filter(user=user).values_list(
        "event_type", "points"
    ):
        totals[event_type]["count"] += 1
        totals[event_type]["points"] += points
    labels = dict(EventType.choices)
    return [
        {
            "event_type": event_type,
            "label": labels[event_type],
            "count": totals[event_type]["count"],
            "points": totals[event_type]["points"],
            "points_per_event": RULES[event_type].points,
        }
        for event_type in EventType.values
        if event_type in totals
    ]


def sync_users(users: Iterable[User | None]) -> None:
    for user in {user.pk: user for user in users if user is not None}.values():
        sync_user(user)


# --- Recommandations ----------------------------------------------------------------


@transaction.atomic
def recommend(
    *, recommender: User, recommended: User, context: str, technology: Any = None
) -> Recommendation:
    if recommender.pk == recommended.pk:
        raise BusinessRuleViolation(
            "Vous ne pouvez pas vous recommander vous-même.", code="self_recommendation"
        )
    if not recommended.is_active:
        raise BusinessRuleViolation("Ce compte n'est plus actif.", code="inactive_account")
    if Recommendation.objects.filter(recommender=recommender, recommended=recommended).exists():
        raise BusinessRuleViolation(
            "Vous avez déjà recommandé ce membre.", code="duplicate_recommendation"
        )
    recommendation = Recommendation.objects.create(
        recommender=recommender,
        recommended=recommended,
        technology=technology,
        context=to_plain_text(context),
    )
    transaction.on_commit(lambda: sync_user(recommended))
    return recommendation
