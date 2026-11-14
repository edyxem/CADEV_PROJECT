"""Endpoints de la messagerie privée (consultation classique, sans temps réel)."""

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from common.schema import errors
from common.throttling import ActionThrottleMixin

from . import services
from .models import Block, Conversation
from .serializers import (
    BlockCreateSerializer,
    BlockSerializer,
    ConversationSerializer,
    ConversationStartSerializer,
    MessageCreateSerializer,
    MessageSerializer,
)

TAG = ["Messagerie"]


@extend_schema_view(
    list=extend_schema(
        tags=TAG, summary="Mes conversations", description="Visibles des seuls participants."
    ),
    retrieve=extend_schema(
        tags=TAG,
        summary="Détail d'une conversation",
        responses={200: ConversationSerializer, **errors(401, 404)},
    ),
    create=extend_schema(
        tags=TAG,
        summary="Écrire à un membre",
        description="Ouvre (ou reprend) la conversation avec ce membre et envoie un "
        "premier message. "
        "Refusé en cas de blocage, dans un sens comme dans l'autre.",
        request=ConversationStartSerializer,
        responses={201: ConversationSerializer, **errors(400, 401, 409, 429)},
    ),
)
class ConversationViewSet(
    ActionThrottleMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    serializer_class = ConversationSerializer
    action_throttle_scopes = {"create": "messaging", "messages": "messaging"}

    def get_queryset(self) -> QuerySet[Conversation]:
        if getattr(self, "swagger_fake_view", False):  # génération du schéma OpenAPI
            return Conversation.objects.none()
        # Seuls les participants voient une conversation : les autres reçoivent un 404.
        return (
            Conversation.objects.filter(participants__user=self.request.user)
            .prefetch_related("participants__user__profile")
            .order_by("-last_message_at", "-created_at")
        )

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = ConversationStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conversation, _ = services.start_conversation(
            sender=request.user,
            recipient=serializer.validated_data["username"],
            content=serializer.validated_data["content"],
        )
        conversation = self.get_queryset().get(pk=conversation.pk)
        return Response(
            ConversationSerializer(conversation, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        tags=TAG,
        summary="Messages d'une conversation",
        description="GET : historique paginé. POST : envoyer (texte brut, 3 liens "
        "http(s) au plus).",
        request=MessageCreateSerializer,
        responses={
            200: MessageSerializer(many=True),
            201: MessageSerializer,
            **errors(400, 401, 404, 409, 429),
        },
    )
    @action(detail=True, methods=["get", "post"])
    def messages(self, request: Request, pk: str | None = None) -> Response:
        conversation = self.get_object()
        context = self.get_serializer_context()
        if request.method == "GET":
            page = self.paginate_queryset(
                conversation.messages.select_related("sender__profile").order_by("-created_at")
            )
            return self.get_paginated_response(
                MessageSerializer(page, many=True, context=context).data
            )
        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = services.send_message(
            conversation=conversation,
            sender=request.user,
            content=serializer.validated_data["content"],
        )
        return Response(
            MessageSerializer(message, context=context).data, status=status.HTTP_201_CREATED
        )

    @extend_schema(
        tags=TAG,
        summary="Marquer la conversation comme lue",
        request=None,
        responses={204: None, **errors(401, 404)},
    )
    @action(detail=True, methods=["post"])
    def read(self, request: Request, pk: str | None = None) -> Response:
        services.mark_read(conversation=self.get_object(), user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    list=extend_schema(tags=TAG, summary="Membres bloqués"),
    create=extend_schema(
        tags=TAG,
        summary="Bloquer un membre",
        description="Un membre bloqué ne peut plus vous écrire (et vous ne pouvez "
        "plus lui écrire).",
        request=BlockCreateSerializer,
        responses={201: BlockSerializer, **errors(400, 401, 409)},
    ),
    destroy=extend_schema(tags=TAG, summary="Débloquer", responses={204: None, **errors(401, 404)}),
)
class BlockViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    serializer_class = BlockSerializer

    def get_queryset(self) -> QuerySet[Block]:
        if getattr(self, "swagger_fake_view", False):  # génération du schéma OpenAPI
            return Block.objects.none()
        return (
            Block.objects.filter(blocker=self.request.user)
            .select_related("blocked__profile")
            .order_by("-created_at")
        )

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = BlockCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        block = services.block(blocker=request.user, blocked=serializer.validated_data["username"])
        return Response(
            BlockSerializer(block, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )
