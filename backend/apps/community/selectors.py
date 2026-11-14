"""Requêtes de lecture : visibilité, compteurs dérivés et tri du fil.

Les compteurs sont calculés par sous-requêtes à partir des données réelles
(§11.5) : ils ne sont jamais stockés ni acceptés depuis le client.
"""

from datetime import timedelta
from typing import Any

from django.db.models import Count, Exists, IntegerField, OuterRef, Q, QuerySet, Subquery, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from common.permissions import is_moderator

from .models import Answer, AnswerVote, Bookmark, Comment, ContentStatus, Post, PostVote

POPULAR_DEFAULT_DAYS = 30


def count_of(queryset: QuerySet, fk: str) -> Coalesce:
    """Sous-requête ``COUNT(*)`` corrélée sur ``fk = OuterRef('pk')``."""
    subquery = (
        queryset.filter(**{fk: OuterRef("pk")})
        .order_by()
        .values(fk)
        .annotate(total=Count("pk"))
        .values("total")
    )
    return Coalesce(Subquery(subquery, output_field=IntegerField()), Value(0))


def _published(model: Any) -> QuerySet:
    return model.all_objects.filter(status=ContentStatus.PUBLISHED)


def annotate_posts(queryset: QuerySet[Post], user: Any) -> QuerySet[Post]:
    queryset = queryset.select_related("author__profile", "category").prefetch_related(
        "tags", "technologies"
    )
    queryset = queryset.annotate(
        vote_count=count_of(PostVote.objects.all(), "post"),
        comment_count=count_of(_published(Comment), "post"),
        answer_count=count_of(_published(Answer), "question"),
        has_accepted_answer=Exists(
            _published(Answer).filter(question=OuterRef("pk"), is_accepted=True)
        ),
    )
    if user is not None and user.is_authenticated:
        voted = PostVote.objects.filter(post=OuterRef("pk"), user=user)
        saved = Bookmark.objects.filter(post=OuterRef("pk"), user=user)
        return queryset.annotate(has_voted=Exists(voted), has_bookmarked=Exists(saved))
    return queryset.annotate(has_voted=Value(False), has_bookmarked=Value(False))


def feed(user: Any) -> QuerySet[Post]:
    """Publications publiques : seule base du fil, des listes et de la recherche."""
    return annotate_posts(Post.all_objects.filter(status=ContentStatus.PUBLISHED), user)


def visible_posts(user: Any) -> QuerySet[Post]:
    """Ce qu'un lecteur peut ouvrir en détail.

    - tout le monde : les publications publiées ;
    - l'auteur : ses brouillons et ses publications masquées ;
    - la modération : tout, y compris les contenus supprimés.
    """
    queryset = Post.all_objects.all()
    if is_moderator(user):
        return annotate_posts(queryset, user)
    condition = Q(status=ContentStatus.PUBLISHED)
    if user is not None and user.is_authenticated:
        condition |= Q(author=user, status__in=[ContentStatus.DRAFT, ContentStatus.HIDDEN])
    return annotate_posts(queryset.filter(condition), user)


def order_feed(queryset: QuerySet[Post], ordering: str, period_days: int | None) -> QuerySet[Post]:
    """Tris explicables du fil (§C.4) : récent, actif, populaire, sans réponse."""
    if ordering == "active":
        return queryset.order_by("-last_activity_at", "-published_at")
    if ordering == "popular":
        since = timezone.now() - timedelta(days=period_days or POPULAR_DEFAULT_DAYS)
        recent_votes = count_of(PostVote.objects.filter(created_at__gte=since), "post")
        return queryset.annotate(recent_votes=recent_votes).order_by(
            "-recent_votes", "-published_at"
        )
    if ordering == "unanswered":
        return queryset.filter(type=Post.Type.QUESTION, answer_count=0).order_by("-published_at")
    return queryset.order_by("-published_at", "-created_at")


def visible_comments(post: Post) -> QuerySet[Comment]:
    """Commentaires publiés, plus les commentaires retirés qui ont encore des réponses.

    Ces derniers sont renvoyés sous forme d'emplacement vide pour ne pas casser
    le fil de discussion.
    """
    visible_replies = Comment.all_objects.filter(
        parent=OuterRef("pk"), status=ContentStatus.PUBLISHED
    )
    return (
        Comment.all_objects.filter(post=post)
        .annotate(has_visible_replies=Exists(visible_replies))
        .filter(Q(status=ContentStatus.PUBLISHED) | Q(has_visible_replies=True))
        .select_related("author__profile")
        .order_by("created_at")
    )


def annotate_answers(queryset: QuerySet[Answer], user: Any) -> QuerySet[Answer]:
    queryset = queryset.select_related("author__profile").annotate(
        vote_count=count_of(AnswerVote.objects.all(), "answer")
    )
    if user is not None and user.is_authenticated:
        voted = AnswerVote.objects.filter(answer=OuterRef("pk"), user=user)
        return queryset.annotate(has_voted=Exists(voted))
    return queryset.annotate(has_voted=Value(False))


def visible_answers(question: Post, user: Any, ordering: str = "votes") -> QuerySet[Answer]:
    queryset = annotate_answers(_published(Answer).filter(question=question), user)
    if ordering == "recent":
        return queryset.order_by("-is_accepted", "-created_at")
    return queryset.order_by("-is_accepted", "-vote_count", "created_at")


def bookmarked_posts(user: Any) -> QuerySet[Post]:
    """Favoris du membre encore publiés, du plus récemment enregistré au plus ancien."""
    saved_at = Bookmark.objects.filter(post=OuterRef("pk"), user=user).values("created_at")[:1]
    return (
        feed(user)
        .filter(bookmarks__user=user)
        .annotate(bookmarked_at=Subquery(saved_at))
        .order_by("-bookmarked_at")
    )
