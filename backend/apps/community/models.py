"""Publications, commentaires, réponses et votes."""

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.db.models import Q

from apps.catalog.models import Category, Tag, Technology
from common.models import BaseModel


class ContentStatus(models.TextChoices):
    DRAFT = "DRAFT", "Brouillon"
    PUBLISHED = "PUBLISHED", "Publié"
    HIDDEN = "HIDDEN", "Masqué par la modération"
    DELETED = "DELETED", "Supprimé"


REMOVED_STATUSES = (ContentStatus.HIDDEN, ContentStatus.DELETED)

# Table des transitions autorisées (§11.11). Les droits de chaque acteur sont
# vérifiés en plus dans ``services`` : l'auteur publie et supprime, la
# modération masque et restaure, seul un admin restaure un contenu supprimé.
CONTENT_TRANSITIONS: dict[str, set[str]] = {
    ContentStatus.DRAFT: {ContentStatus.PUBLISHED, ContentStatus.DELETED},
    ContentStatus.PUBLISHED: {ContentStatus.HIDDEN, ContentStatus.DELETED},
    ContentStatus.HIDDEN: {ContentStatus.PUBLISHED, ContentStatus.DELETED},
    ContentStatus.DELETED: {ContentStatus.PUBLISHED},
}


class VisibleQuerySet(models.QuerySet):
    def published(self) -> "VisibleQuerySet":
        return self.filter(status=ContentStatus.PUBLISHED)


class VisibleManager(models.Manager.from_queryset(VisibleQuerySet)):
    """Exclut les contenus masqués ou supprimés ; ``all_objects`` voit tout."""

    def get_queryset(self) -> VisibleQuerySet:
        return super().get_queryset().exclude(status__in=REMOVED_STATUSES)


AllManager = models.Manager.from_queryset(VisibleQuerySet)


class Post(BaseModel):
    class Type(models.TextChoices):
        DISCUSSION = "DISCUSSION", "Discussion"
        QUESTION = "QUESTION", "Question"
        ARTICLE = "ARTICLE", "Article / tutoriel"
        ANNOUNCEMENT = "ANNOUNCEMENT", "Annonce communautaire"
        PROJECT_UPDATE = "PROJECT_UPDATE", "Mise à jour de projet"

    TITLE_MIN_LENGTH = 8
    TITLE_MAX_LENGTH = 150
    CONTENT_MAX_LENGTH = 30000

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="posts"
    )
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, null=True, blank=True, related_name="posts"
    )
    type = models.CharField(max_length=16, choices=Type.choices, default=Type.DISCUSSION)
    title = models.CharField(max_length=TITLE_MAX_LENGTH)
    content = models.TextField(blank=True)
    environment = models.TextField(
        "environnement / contexte",
        blank=True,
        max_length=2000,
        help_text="Questions : versions, système, ce qui a déjà été essayé.",
    )
    status = models.CharField(
        max_length=16, choices=ContentStatus.choices, default=ContentStatus.PUBLISHED
    )
    published_at = models.DateTimeField(null=True, blank=True)
    last_activity_at = models.DateTimeField(null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name="posts")
    technologies = models.ManyToManyField(Technology, blank=True, related_name="posts")
    search_vector = SearchVectorField(null=True, editable=False)

    all_objects = AllManager()
    objects = VisibleManager()

    class Meta:
        verbose_name = "publication"
        verbose_name_plural = "publications"
        default_manager_name = "all_objects"
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["status", "-published_at"], name="post_feed_idx"),
            models.Index(fields=["type", "status"], name="post_type_idx"),
            models.Index(fields=["status", "-last_activity_at"], name="post_activity_idx"),
            models.Index(fields=["category", "status"], name="post_category_idx"),
            models.Index(fields=["author", "status"], name="post_author_idx"),
            GinIndex(fields=["search_vector"], name="post_search_idx"),
            GinIndex(fields=["title"], opclasses=["gin_trgm_ops"], name="post_title_trgm_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~Q(status=ContentStatus.PUBLISHED) | Q(published_at__isnull=False),
                name="post_published_has_date",
            ),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def is_question(self) -> bool:
        return self.type == self.Type.QUESTION

    @property
    def is_published(self) -> bool:
        return self.status == ContentStatus.PUBLISHED


class Comment(BaseModel):
    """Commentaire d'une publication, avec un seul niveau d'imbrication."""

    MAX_LENGTH = 5000

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="comments"
    )
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies"
    )
    content = models.TextField(max_length=MAX_LENGTH)
    status = models.CharField(
        max_length=16, choices=ContentStatus.choices, default=ContentStatus.PUBLISHED
    )

    all_objects = AllManager()
    objects = VisibleManager()

    class Meta:
        verbose_name = "commentaire"
        verbose_name_plural = "commentaires"
        default_manager_name = "all_objects"
        ordering = ["created_at"]
        indexes = [models.Index(fields=["post", "status", "created_at"], name="comment_post_idx")]
        constraints = [
            models.CheckConstraint(
                condition=~Q(status=ContentStatus.DRAFT), name="comment_not_draft"
            ),
        ]

    def __str__(self) -> str:
        return f"Commentaire de {self.author} sur « {self.post} »"


class Answer(BaseModel):
    """Réponse à une question ; une seule peut être acceptée par question."""

    MAX_LENGTH = 30000

    question = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="answers")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="answers"
    )
    content = models.TextField()
    is_accepted = models.BooleanField(default=False)
    accepted_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=16, choices=ContentStatus.choices, default=ContentStatus.PUBLISHED
    )

    all_objects = AllManager()
    objects = VisibleManager()

    class Meta:
        verbose_name = "réponse"
        verbose_name_plural = "réponses"
        default_manager_name = "all_objects"
        ordering = ["-is_accepted", "created_at"]
        indexes = [
            models.Index(fields=["question", "status"], name="answer_question_idx"),
            models.Index(fields=["author", "status"], name="answer_author_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["question"],
                condition=Q(is_accepted=True),
                name="answer_one_accepted_per_question",
            ),
            models.CheckConstraint(
                condition=Q(is_accepted=False) | Q(accepted_at__isnull=False),
                name="answer_accepted_has_date",
            ),
            models.CheckConstraint(
                condition=~Q(status=ContentStatus.DRAFT), name="answer_not_draft"
            ),
        ]

    def __str__(self) -> str:
        return f"Réponse de {self.author} à « {self.question} »"


class PostVote(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="post_votes"
    )
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="votes")

    class Meta:
        verbose_name = "vote sur publication"
        verbose_name_plural = "votes sur publications"
        constraints = [models.UniqueConstraint(fields=["user", "post"], name="post_vote_unique")]


class AnswerVote(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="answer_votes"
    )
    answer = models.ForeignKey(Answer, on_delete=models.CASCADE, related_name="votes")

    class Meta:
        verbose_name = "vote sur réponse"
        verbose_name_plural = "votes sur réponses"
        constraints = [
            models.UniqueConstraint(fields=["user", "answer"], name="answer_vote_unique")
        ]


class Bookmark(BaseModel):
    """Publication enregistrée par un membre (P1)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookmarks"
    )
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="bookmarks")

    class Meta:
        verbose_name = "favori"
        verbose_name_plural = "favoris"
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["user", "post"], name="bookmark_unique")]
