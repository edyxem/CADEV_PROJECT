"""Boîte de notifications personnelle."""

from django.db.models import QuerySet
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from common.schema import errors

from . import services
from .models import Notification
from .serializers import MarkedSerializer, NotificationSerializer, UnreadCountSerializer

TAG = ["Notifications"]


@extend_schema_view(
    list=extend_schema(
        tags=TAG,
        summary="Mes notifications",
        description="Réservé au destinataire. Paginé, du plus récent au plus ancien.",
        parameters=[OpenApiParameter("is_read", bool, description="Filtrer lues / non lues.")],
        responses={200: NotificationSerializer(many=True), **errors(401)},
    ),
)
class NotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self) -> QuerySet[Notification]:
        # Filtrer par destinataire rend les notifications d'autrui introuvables (404).
        queryset = Notification.objects.filter(recipient=self.request.user).select_related("actor")
        is_read = self.request.query_params.get("is_read")
        if is_read in {"true", "false"}:
            queryset = queryset.filter(is_read=is_read == "true")
        return queryset

    @extend_schema(
        tags=TAG,
        summary="Marquer comme lue",
        request=None,
        responses={200: NotificationSerializer, **errors(401, 404)},
    )
    @action(detail=True, methods=["post"])
    def read(self, request: Request, pk: str | None = None) -> Response:
        notification = services.mark_read(self.get_object())
        return Response(self.get_serializer(notification).data)

    @extend_schema(
        tags=TAG,
        summary="Tout marquer comme lu",
        request=None,
        responses={200: MarkedSerializer, **errors(401)},
    )
    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request: Request) -> Response:
        return Response({"updated": services.mark_all_read(request.user)})

    @extend_schema(
        tags=TAG,
        summary="Nombre de notifications non lues",
        responses={200: UnreadCountSerializer, **errors(401)},
    )
    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request: Request) -> Response:
        unread = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({"unread": unread})
