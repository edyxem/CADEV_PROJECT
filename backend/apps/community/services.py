"""Règles métier des échanges communautaires."""

from collections.abc import Iterable
from typing import Any

from django.contrib.postgres.search import SearchVector
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import exceptions

from apps.accounts.models import User
from apps.notifications.models import Notification
from apps.notifications.services import notify
from common.exceptions import BusinessRuleViolation
from common.permissions import is_admin, is_moderator
from common.sanitization import has_visible_text, sanitize_rich_text, to_plain_text
from common.search import SEARCH_CONFIG
from common.transitions import ensure_transition

from .models import (
    CONTENT_TRANSITIONS,
    Answer,
    AnswerVote,
    Comment,
    ContentStatus,
    Post,
    PostVote,
)

VOTE_MILESTONES = frozenset({1, 5, 10, 25, 50, 100})
MODERATOR_ONLY_TYPES = {Post.Type.ANNOUNCEMENT}
EMPTY_CONTENT = "Le contenu ne peut pas être vide."
Moderable = Post | Comment | Answer


def post_url(post: Post) -> str:
    return f"/publications/{post.pk}"


# --- Contenu ---------------------------------------------------------------------


def clean_rich_content(value: str, *, required: bool = True) -> str:
    cleaned = sanitize_rich_text(value)
    if required and not has_visible_text(cleaned):
        raise exceptions.ValidationError({"content": [EMPTY_CONTENT]})
    return cleaned


def refresh_search_vector(post: Post) -> None:
    """Indexe titre (poids A), contenu (B) et environnement (C), en français sans accents."""
    Post.all_objects.filter(pk=post.pk).update(
        search_vector=SearchVector("title", weight="A", config=SEARCH_CONFIG)
        + SearchVector("content", weight="B", config=SEARCH_CONFIG)
        + SearchVector("environment", weight="C", config=SEARCH_CONFIG)
    )


def _touch_activity(post: Post) -> None:
    Post.all_objects.filter(pk=post.pk).update(last_activity_at=timezone.now())


def _ensure_writable(obj: Moderable) -> None:
    if obj.status in (ContentStatus.HIDDEN, ContentStatus.DELETED):
        raise BusinessRuleViolation(
            "Ce contenu a été retiré et ne peut plus être modifié.", code="content_removed"
        )


def _ensure_author(obj: Moderable, actor: User) -> None:
    if obj.author_id != actor.pk:
        raise exceptions.PermissionDenied("Vous ne pouvez modifier que vos propres contenus.")


# --- Publications ----------------------------------------------------------------


def _apply_relations(post: Post, tags: Iterable | None, technologies: Iterable | None) -> None:
    if tags is not None:
        post.tags.set(tags)
    if technologies is not None:
        post.technologies.set(technologies)


@transaction.atomic
def create_post(*, author: User, data: dict[str, Any]) -> Post:
    data = dict(data)
    tags, technologies = data.pop("tags", None), data.pop("technologies", None)
    status = data.pop("status", ContentStatus.PUBLISHED)
    if data.get("type") in MODERATOR_ONLY_TYPES and not is_moderator(author):
        raise exceptions.PermissionDenied("Les annonces sont réservées à la modération.")

    post = Post(author=author, status=status, **data)
    post.content = clean_rich_content(post.content, required=status == ContentStatus.PUBLISHED)
    post.environment = to_plain_text(post.environment)
    if status == ContentStatus.PUBLISHED:
        post.published_at = post.last_activity_at = timezone.now()
    post.save()
    _apply_relations(post, tags, technologies)
    refresh_search_vector(post)
    return post


@transaction.atomic
def update_post(*, post: Post, actor: User, data: dict[str, Any]) -> Post:
    _ensure_author(post, actor)
    _ensure_writable(post)
    data = dict(data)
    tags, technologies = data.pop("tags", None), data.pop("technologies", None)
    target_status = data.pop("status", post.status)
    if data.get("type") in MODERATOR_ONLY_TYPES and not is_moderator(actor):
        raise exceptions.PermissionDenied("Les annonces sont réservées à la modération.")

    for field, value in data.items():
        setattr(post, field, value)
    if target_status != post.status:
        if target_status != ContentStatus.PUBLISHED:
            raise BusinessRuleViolation(
                "Une publication ne peut pas redevenir un brouillon.", code="invalid_transition"
            )
        ensure_transition(CONTENT_TRANSITIONS, post.status, target_status)
        post.status = target_status
        post.published_at = post.last_activity_at = timezone.now()
    post.content = clean_rich_content(post.content, required=post.is_published)
    post.environment = to_plain_text(post.environment)
    post.save()
    _apply_relations(post, tags, technologies)
    refresh_search_vector(post)
    return post


def delete_post(*, post: Post, actor: User) -> None:
    """Suppression logique par l'auteur : les réponses et la traçabilité sont conservées."""
    _ensure_author(post, actor)
    _ensure_writable(post)
    _set_status(post, ContentStatus.DELETED)


# --- Statut (auteur et modération) -----------------------------------------------


def _set_status(obj: Moderable, target: str) -> str:
    previous = obj.status
    ensure_transition(CONTENT_TRANSITIONS, previous, target)
    obj.status = target
    fields = ["status", "updated_at"]
    if isinstance(obj, Post) and target == ContentStatus.PUBLISHED and obj.published_at is None:
        obj.published_at = timezone.now()
        fields.append("published_at")
    if isinstance(obj, Answer) and target != ContentStatus.PUBLISHED:
        # Toujours réinitialisé : l'instance reçue peut être antérieure à l'acceptation.
        obj.is_accepted, obj.accepted_at = False, None
        fields += ["is_accepted", "accepted_at"]
    obj.save(update_fields=fields)
    return previous


@transaction.atomic
def moderate_status(obj: Moderable, *, target: str, actor: User) -> str:
    """Change le statut d'un contenu au titre de la modération ; renvoie l'ancien statut.

    La journalisation est faite par le module ``moderation``, seul appelant.
    """
    if not is_moderator(actor):
        raise exceptions.PermissionDenied("Action réservée à la modération.")
    restoring_deleted = obj.status == ContentStatus.DELETED and target == ContentStatus.PUBLISHED
    if restoring_deleted and not is_admin(actor):
        raise exceptions.PermissionDenied(
            "Seul un administrateur peut restaurer un contenu supprimé."
        )
    if obj.status == ContentStatus.DRAFT:
        raise BusinessRuleViolation("Un brouillon n'est pas modérable.", code="invalid_transition")
    return _set_status(obj, target)


# --- Commentaires ----------------------------------------------------------------


def _ensure_published(post: Post) -> None:
    if not post.is_published:
        raise BusinessRuleViolation(
            "Cette publication n'accepte pas de participation.", code="post_not_published"
        )


@transaction.atomic
def add_comment(*, post: Post, author: User, content: str, parent: Comment | None) -> Comment:
    _ensure_published(post)
    if parent is not None:
        if parent.post_id != post.pk:
            raise exceptions.ValidationError(
                {"parent": ["Ce commentaire n'appartient pas à la publication."]}
            )
        if parent.parent_id is not None:
            raise exceptions.ValidationError(
                {"parent": ["Les réponses sont limitées à un seul niveau."]}
            )
        if parent.status != ContentStatus.PUBLISHED:
            raise exceptions.ValidationError({"parent": ["Ce commentaire n'est plus disponible."]})

    comment = Comment.objects.create(
        post=post, author=author, parent=parent, content=clean_rich_content(content)
    )
    _touch_activity(post)
    notify(
        post.author,
        type=Notification.Type.COMMENT_CREATED,
        title=f"{author.username} a commenté « {post.title} »",
        actor=author,
        target=post,
        target_url=post_url(post),
    )
    if parent is not None and parent.author_id != post.author_id:
        notify(
            parent.author,
            type=Notification.Type.COMMENT_REPLY,
            title=f"{author.username} a répondu à votre commentaire",
            actor=author,
            target=post,
            target_url=post_url(post),
        )
    return comment


def update_comment(*, comment: Comment, actor: User, content: str) -> Comment:
    _ensure_author(comment, actor)
    _ensure_writable(comment)
    comment.content = clean_rich_content(content)
    comment.save(update_fields=["content", "updated_at"])
    return comment


def delete_comment(*, comment: Comment, actor: User) -> None:
    _ensure_author(comment, actor)
    _ensure_writable(comment)
    _set_status(comment, ContentStatus.DELETED)


# --- Réponses --------------------------------------------------------------------


@transaction.atomic
def add_answer(*, question: Post, author: User, content: str) -> Answer:
    if not question.is_question:
        raise BusinessRuleViolation(
            "Seules les questions acceptent des réponses.", code="not_a_question"
        )
    _ensure_published(question)
    answer = Answer.objects.create(
        question=question, author=author, content=clean_rich_content(content)
    )
    _touch_activity(question)
    notify(
        question.author,
        type=Notification.Type.ANSWER_CREATED,
        title=f"{author.username} a répondu à « {question.title} »",
        actor=author,
        target=question,
        target_url=post_url(question),
    )
    return answer


def update_answer(*, answer: Answer, actor: User, content: str) -> Answer:
    _ensure_author(answer, actor)
    _ensure_writable(answer)
    answer.content = clean_rich_content(content)
    answer.save(update_fields=["content", "updated_at"])
    return answer


@transaction.atomic
def delete_answer(*, answer: Answer, actor: User) -> None:
    _ensure_author(answer, actor)
    _ensure_writable(answer)
    _set_status(answer, ContentStatus.DELETED)


@transaction.atomic
def accept_answer(*, answer: Answer, actor: User) -> Answer:
    """Seul l'auteur de la question accepte, jamais sa propre réponse, une seule à la fois."""
    question = Post.all_objects.select_for_update().get(pk=answer.question_id)
    answer = Answer.all_objects.select_for_update().get(pk=answer.pk)
    if question.author_id != actor.pk:
        raise exceptions.PermissionDenied("Seul l'auteur de la question peut accepter une réponse.")
    if answer.author_id == actor.pk:
        raise BusinessRuleViolation(
            "Vous ne pouvez pas accepter votre propre réponse.", code="self_accept"
        )
    _ensure_published(question)
    if answer.status != ContentStatus.PUBLISHED:
        raise BusinessRuleViolation("Cette réponse n'est plus disponible.", code="answer_removed")
    if answer.is_accepted:
        return answer

    Answer.all_objects.filter(question=question, is_accepted=True).update(
        is_accepted=False, accepted_at=None
    )
    answer.is_accepted, answer.accepted_at = True, timezone.now()
    answer.save(update_fields=["is_accepted", "accepted_at", "updated_at"])
    notify(
        answer.author,
        type=Notification.Type.ANSWER_ACCEPTED,
        title=f"Votre réponse à « {question.title} » a été acceptée",
        actor=actor,
        target=question,
        target_url=post_url(question),
    )
    return answer


@transaction.atomic
def unaccept_answer(*, answer: Answer, actor: User) -> Answer:
    question = Post.all_objects.select_for_update().get(pk=answer.question_id)
    if question.author_id != actor.pk:
        raise exceptions.PermissionDenied(
            "Seul l'auteur de la question peut retirer l'acceptation."
        )
    Answer.all_objects.filter(pk=answer.pk).update(is_accepted=False, accepted_at=None)
    answer.refresh_from_db()
    return answer


# --- Votes -----------------------------------------------------------------------


def _toggle_vote(
    *, vote_model: Any, target_field: str, target: Post | Answer, user: User, active: bool | None
) -> tuple[bool, int]:
    """Bascule ou fixe un vote de façon idempotente ; renvoie (a voté, total).

    Le verrou sur la cible sérialise les requêtes concurrentes ; la contrainte
    d'unicité en base reste le dernier rempart contre les doublons.
    """
    if target.author_id == user.pk:
        raise BusinessRuleViolation(
            "Vous ne pouvez pas voter pour votre propre contenu.", code="self_vote"
        )
    if target.status != ContentStatus.PUBLISHED:
        raise BusinessRuleViolation("Ce contenu n'accepte plus de vote.", code="content_removed")

    type(target).all_objects.select_for_update().filter(pk=target.pk).first()
    lookup = {"user": user, target_field: target}
    exists = vote_model.objects.filter(**lookup).exists()
    wanted = (not exists) if active is None else active
    created = False
    if wanted and not exists:
        try:
            with transaction.atomic():
                vote_model.objects.create(**lookup)
            created = True
        except IntegrityError:
            created = False
    elif not wanted and exists:
        vote_model.objects.filter(**lookup).delete()

    total = vote_model.objects.filter(**{target_field: target}).count()
    if created and total in VOTE_MILESTONES:
        plural = "s" if total > 1 else ""
        notify(
            target.author,
            type=Notification.Type.VOTE_MILESTONE,
            title=f"Votre contribution a atteint {total} vote{plural} utile{plural}",
            target=target if isinstance(target, Post) else target.question,
            target_url=post_url(target if isinstance(target, Post) else target.question),
        )
    return wanted, total


@transaction.atomic
def vote_post(*, post: Post, user: User, active: bool | None = None) -> tuple[bool, int]:
    return _toggle_vote(
        vote_model=PostVote, target_field="post", target=post, user=user, active=active
    )


@transaction.atomic
def vote_answer(*, answer: Answer, user: User, active: bool | None = None) -> tuple[bool, int]:
    return _toggle_vote(
        vote_model=AnswerVote, target_field="answer", target=answer, user=user, active=active
    )
