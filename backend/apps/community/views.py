"""Endpoints du fil, des publications, commentaires, réponses et votes."""

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.request import Request
from rest_framework.response import Response

from common.schema import errors
from common.throttling import ActionThrottleMixin

from . import selectors, services
from .filters import PostFilter
from .models import Answer, Comment, ContentStatus, Post
from .serializers import (
    AnswerSerializer,
    AnswerWriteSerializer,
    BookmarkResultSerializer,
    CommentSerializer,
    CommentWriteSerializer,
    PostDetailSerializer,
    PostListSerializer,
    PostWriteSerializer,
    VoteInputSerializer,
    VoteResultSerializer,
)

POSTS_TAG = ["Publications"]
QA_TAG = ["Questions et réponses"]
FEED_PARAMETERS = [
    OpenApiParameter(
        "ordering",
        str,
        enum=["recent", "active", "popular", "unanswered"],
        description="recent (défaut), active (activité récente), popular (votes sur la "
        "période), unanswered (questions sans réponse).",
    ),
    OpenApiParameter("period", int, description="Fenêtre en jours du tri popular (défaut 30)."),
]
MEMBER_WRITE = "Réservé aux membres connectés."
AUTHOR_ONLY = "Réservé à l'auteur ; un contenu masqué ou supprimé n'est plus modifiable."


def _period(request: Request) -> int | None:
    try:
        value = int(request.query_params.get("period", ""))
    except ValueError:
        return None
    return min(max(value, 1), 365)


def _vote_response(voted: bool, count: int) -> Response:
    return Response({"voted": voted, "vote_count": count})


@extend_schema_view(
    list=extend_schema(
        tags=POSTS_TAG,
        summary="Fil communautaire",
        description="Accès public. Publications publiées uniquement, paginées.",
        parameters=FEED_PARAMETERS,
    ),
    retrieve=extend_schema(
        tags=POSTS_TAG,
        summary="Consulter une publication",
        description="Accès public pour une publication publiée ; l'auteur voit ses brouillons.",
        responses={200: PostDetailSerializer, **errors(404)},
    ),
    create=extend_schema(
        tags=POSTS_TAG,
        summary="Publier une discussion, une question, un article",
        description=f"{MEMBER_WRITE} Les annonces sont réservées à la modération. Le contenu "
        "HTML est assaini (liste blanche de balises).",
        request=PostWriteSerializer,
        responses={201: PostDetailSerializer, **errors(400, 401, 403, 429)},
    ),
    partial_update=extend_schema(
        tags=POSTS_TAG,
        summary="Modifier sa publication",
        description=f"{AUTHOR_ONLY} `status=PUBLISHED` publie un brouillon.",
        request=PostWriteSerializer,
        responses={200: PostDetailSerializer, **errors(400, 401, 403, 404, 409)},
    ),
    destroy=extend_schema(
        tags=POSTS_TAG,
        summary="Supprimer sa publication",
        description=f"{AUTHOR_ONLY} Suppression logique.",
        responses={204: None, **errors(401, 403, 404, 409)},
    ),
)
class PostViewSet(ActionThrottleMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    filterset_class = PostFilter
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    action_throttle_scopes = {"create": "content_create", "comments": "comment_create"}

    def get_queryset(self) -> QuerySet[Post]:
        if getattr(self, "swagger_fake_view", False):  # génération du schéma OpenAPI
            return Post.all_objects.none()
        user = self.request.user
        if self.action == "list":
            ordering = self.request.query_params.get("ordering", "recent")
            return selectors.order_feed(selectors.feed(user), ordering, _period(self.request))
        if self.action == "bookmarks":
            return selectors.bookmarked_posts(user)
        if self.action == "mine":
            own = Post.all_objects.filter(author=user).exclude(status=ContentStatus.DELETED)
            return selectors.annotate_posts(own, user).order_by("-created_at")
        return selectors.visible_posts(user)

    def get_serializer_class(self):
        if self.action in {"list", "mine", "bookmarks"}:
            return PostListSerializer
        if self.action in {"create", "partial_update"}:
            return PostWriteSerializer
        return PostDetailSerializer

    def _detail(self, post: Post, status_code: int = status.HTTP_200_OK) -> Response:
        post = selectors.visible_posts(self.request.user).get(pk=post.pk)
        context = self.get_serializer_context()
        return Response(PostDetailSerializer(post, context=context).data, status=status_code)

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = PostWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        post = services.create_post(author=request.user, data=serializer.validated_data)
        return self._detail(post, status.HTTP_201_CREATED)

    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        post = self.get_object()
        serializer = PostWriteSerializer(post, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        services.update_post(post=post, actor=request.user, data=serializer.validated_data)
        return self._detail(post)

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        services.delete_post(post=self.get_object(), actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        tags=POSTS_TAG,
        summary="Mes publications",
        description="Réservé au membre connecté : publications et brouillons non supprimés.",
        responses={200: PostListSerializer(many=True), **errors(401)},
    )
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def mine(self, request: Request) -> Response:
        return super().list(request)

    @extend_schema(
        tags=POSTS_TAG,
        summary="Mes favoris",
        description="Publications enregistrées encore publiées, de la plus récente à la plus "
        "ancienne.",
        responses={200: PostListSerializer(many=True), **errors(401)},
    )
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def bookmarks(self, request: Request) -> Response:
        return super().list(request)

    @extend_schema(
        tags=POSTS_TAG,
        summary="Ajouter / retirer un favori",
        description="POST sans corps bascule ; `active` fixe l'état ; DELETE retire.",
        request=VoteInputSerializer,
        responses={200: BookmarkResultSerializer, **errors(401, 404, 409)},
    )
    @action(detail=True, methods=["post", "delete"], permission_classes=[IsAuthenticated])
    def bookmark(self, request: Request, pk: str | None = None) -> Response:
        post = self.get_object()
        active = False
        if request.method == "POST":
            serializer = VoteInputSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            active = serializer.validated_data["active"]
        bookmarked = services.bookmark_post(post=post, user=request.user, active=active)
        return Response({"bookmarked": bookmarked})

    @extend_schema(
        tags=POSTS_TAG,
        summary="Voter / retirer son vote",
        description=f"{MEMBER_WRITE} Un seul vote par membre ; voter pour son propre contenu est "
        "interdit. POST sans corps bascule ; `active` fixe l'état (idempotent) ; DELETE retire.",
        request=VoteInputSerializer,
        responses={200: VoteResultSerializer, **errors(401, 404, 409)},
    )
    @action(detail=True, methods=["post", "delete"], permission_classes=[IsAuthenticated])
    def vote(self, request: Request, pk: str | None = None) -> Response:
        post = self.get_object()
        if request.method == "DELETE":
            active = False
        else:
            serializer = VoteInputSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            active = serializer.validated_data["active"]
        return _vote_response(*services.vote_post(post=post, user=request.user, active=active))

    @extend_schema(
        tags=POSTS_TAG,
        summary="Commentaires d'une publication",
        description="GET public. POST réservé aux membres (un seul niveau de réponse via "
        "`parent`). Un commentaire retiré qui a des réponses reste affiché vide.",
        request=CommentWriteSerializer,
        responses={
            200: CommentSerializer(many=True),
            201: CommentSerializer,
            **errors(400, 401, 404, 409, 429),
        },
    )
    @action(detail=True, methods=["get", "post"])
    def comments(self, request: Request, pk: str | None = None) -> Response:
        post = self.get_object()
        if request.method == "GET":
            page = self.paginate_queryset(selectors.visible_comments(post))
            data = CommentSerializer(page, many=True, context=self.get_serializer_context()).data
            return self.get_paginated_response(data)

        serializer = CommentWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        parent_id = serializer.validated_data.get("parent")
        parent = get_object_or_404(Comment.all_objects, pk=parent_id) if parent_id else None
        comment = services.add_comment(
            post=post,
            author=request.user,
            content=serializer.validated_data["content"],
            parent=parent,
        )
        return Response(
            CommentSerializer(comment, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    list=extend_schema(
        tags=QA_TAG,
        summary="Lister les questions",
        description="Accès public. Mêmes filtres que le fil ; `unanswered=true` ou "
        "`ordering=unanswered` pour les questions sans réponse.",
        parameters=FEED_PARAMETERS,
    ),
    retrieve=extend_schema(
        tags=QA_TAG,
        summary="Consulter une question",
        responses={200: PostDetailSerializer, **errors(404)},
    ),
)
class QuestionViewSet(ActionThrottleMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    filterset_class = PostFilter
    action_throttle_scopes = {"answers": "content_create"}

    def get_queryset(self) -> QuerySet[Post]:
        user = self.request.user
        if self.action == "list":
            ordering = self.request.query_params.get("ordering", "recent")
            queryset = selectors.feed(user).filter(type=Post.Type.QUESTION)
            return selectors.order_feed(queryset, ordering, _period(self.request))
        return selectors.visible_posts(user).filter(type=Post.Type.QUESTION)

    def get_serializer_class(self):
        return PostListSerializer if self.action == "list" else PostDetailSerializer

    @extend_schema(
        tags=QA_TAG,
        summary="Réponses d'une question",
        description="GET public : la réponse acceptée d'abord, puis par votes "
        "(`ordering=recent` pour trier par date). POST réservé aux membres.",
        parameters=[OpenApiParameter("ordering", str, enum=["votes", "recent"])],
        request=AnswerWriteSerializer,
        responses={
            200: AnswerSerializer(many=True),
            201: AnswerSerializer,
            **errors(400, 401, 404, 409, 429),
        },
    )
    @action(detail=True, methods=["get", "post"])
    def answers(self, request: Request, pk: str | None = None) -> Response:
        question = self.get_object()
        context = self.get_serializer_context()
        if request.method == "GET":
            ordering = request.query_params.get("ordering", "votes")
            page = self.paginate_queryset(
                selectors.visible_answers(question, request.user, ordering)
            )
            return self.get_paginated_response(
                AnswerSerializer(page, many=True, context=context).data
            )

        serializer = AnswerWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        answer = services.add_answer(
            question=question, author=request.user, content=serializer.validated_data["content"]
        )
        answer = selectors.annotate_answers(
            Answer.all_objects.filter(pk=answer.pk), request.user
        ).get()
        return Response(
            AnswerSerializer(answer, context=context).data, status=status.HTTP_201_CREATED
        )


@extend_schema_view(
    partial_update=extend_schema(
        tags=POSTS_TAG,
        summary="Modifier son commentaire",
        description=AUTHOR_ONLY,
        request=CommentWriteSerializer,
        responses={200: CommentSerializer, **errors(400, 401, 403, 404, 409)},
    ),
    destroy=extend_schema(
        tags=POSTS_TAG,
        summary="Supprimer son commentaire",
        description=f"{AUTHOR_ONLY} Suppression logique.",
        responses={204: None, **errors(401, 403, 404, 409)},
    ),
)
class CommentViewSet(mixins.UpdateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CommentSerializer
    http_method_names = ["patch", "delete", "options"]

    def get_queryset(self) -> QuerySet[Comment]:
        return Comment.objects.filter(post__status=ContentStatus.PUBLISHED).select_related(
            "author__profile"
        )

    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        serializer = CommentWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = services.update_comment(
            comment=self.get_object(),
            actor=request.user,
            content=serializer.validated_data["content"],
        )
        return Response(CommentSerializer(comment, context=self.get_serializer_context()).data)

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        services.delete_comment(comment=self.get_object(), actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    retrieve=extend_schema(
        tags=QA_TAG,
        summary="Consulter une réponse",
        responses={200: AnswerSerializer, **errors(404)},
    ),
    partial_update=extend_schema(
        tags=QA_TAG,
        summary="Modifier sa réponse",
        description=AUTHOR_ONLY,
        request=AnswerWriteSerializer,
        responses={200: AnswerSerializer, **errors(400, 401, 403, 404, 409)},
    ),
    destroy=extend_schema(
        tags=QA_TAG,
        summary="Supprimer sa réponse",
        description=f"{AUTHOR_ONLY} Suppression logique ; une réponse acceptée perd ce statut.",
        responses={204: None, **errors(401, 403, 404, 409)},
    ),
)
class AnswerViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = AnswerSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self) -> QuerySet[Answer]:
        queryset = Answer.objects.filter(question__status=ContentStatus.PUBLISHED)
        return selectors.annotate_answers(queryset, self.request.user)

    def _detail(self, answer: Answer) -> Response:
        answer = self.get_queryset().get(pk=answer.pk)
        return Response(AnswerSerializer(answer, context=self.get_serializer_context()).data)

    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        serializer = AnswerWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        answer = services.update_answer(
            answer=self.get_object(),
            actor=request.user,
            content=serializer.validated_data["content"],
        )
        return self._detail(answer)

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        services.delete_answer(answer=self.get_object(), actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        tags=QA_TAG,
        summary="Voter / retirer son vote sur une réponse",
        description="Mêmes règles que le vote sur une publication.",
        request=VoteInputSerializer,
        responses={200: VoteResultSerializer, **errors(401, 404, 409)},
    )
    @action(detail=True, methods=["post", "delete"], permission_classes=[IsAuthenticated])
    def vote(self, request: Request, pk: str | None = None) -> Response:
        answer = self.get_object()
        if request.method == "DELETE":
            active = False
        else:
            serializer = VoteInputSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            active = serializer.validated_data["active"]
        return _vote_response(
            *services.vote_answer(answer=answer, user=request.user, active=active)
        )

    @extend_schema(
        tags=QA_TAG,
        summary="Accepter / retirer l'acceptation d'une réponse",
        description="Réservé à l'auteur de la question, qui ne peut pas accepter sa propre "
        "réponse. Accepter une autre réponse remplace l'acceptation précédente.",
        request=None,
        responses={200: AnswerSerializer, **errors(401, 403, 404, 409)},
    )
    @action(detail=True, methods=["post", "delete"], permission_classes=[IsAuthenticated])
    def accept(self, request: Request, pk: str | None = None) -> Response:
        answer = self.get_object()
        if request.method == "DELETE":
            answer = services.unaccept_answer(answer=answer, actor=request.user)
        else:
            answer = services.accept_answer(answer=answer, actor=request.user)
        return self._detail(answer)
