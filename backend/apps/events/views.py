"""Endpoints des événements."""

from django.db.models import Count, Q, QuerySet
from django.http import Http404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.request import Request
from rest_framework.response import Response

from common.permissions import is_moderator
from common.schema import errors

from . import services
from .models import Event, EventRegistration
from .serializers import EventSerializer, EventWriteSerializer, RegistrationSerializer

TAG = ["Événements"]


@extend_schema_view(
    list=extend_schema(
        tags=TAG,
        summary="Agenda",
        description="Accès public. `when=upcoming` (défaut), `past` ou `all`.",
        parameters=[
            OpenApiParameter("when", str, enum=["upcoming", "past", "all"]),
            OpenApiParameter("format", str, enum=Event.Format.values),
            OpenApiParameter("kind", str, enum=Event.Kind.values),
            OpenApiParameter("community", str),
            OpenApiParameter("technology", str),
        ],
    ),
    retrieve=extend_schema(
        tags=TAG,
        summary="Détail d'un événement",
        description="Le lien de connexion n'est communiqué qu'aux inscrits et à l'organisateur.",
    ),
    create=extend_schema(
        tags=TAG,
        summary="Publier un événement",
        description="Réservé aux membres ; dans une communauté, réservé à ses membres.",
        request=EventWriteSerializer,
        responses={201: EventSerializer, **errors(400, 401, 403, 429)},
    ),
    partial_update=extend_schema(
        tags=TAG,
        summary="Modifier un événement",
        description="Réservé à l'organisateur.",
        request=EventWriteSerializer,
        responses={200: EventSerializer, **errors(400, 401, 403, 404, 409)},
    ),
)
class EventViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = EventSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    throttle_scope = "content_create"

    def get_queryset(self) -> QuerySet[Event]:
        if getattr(self, "swagger_fake_view", False):  # génération du schéma OpenAPI
            return Event.objects.none()
        queryset = (
            Event.objects.select_related("organizer__profile", "community", "category")
            .prefetch_related("technologies")
            .annotate(
                registered_count=Count(
                    "registrations",
                    filter=Q(registrations__status=EventRegistration.Status.REGISTERED),
                )
            )
        )
        if not is_moderator(self.request.user):
            queryset = queryset.filter(hidden_by_moderation=False)
        if self.action == "mine":
            return queryset.filter(
                registrations__user=self.request.user,
                registrations__status=EventRegistration.Status.REGISTERED,
            )
        if self.action != "list":
            return queryset
        params, now = self.request.query_params, timezone.now()
        when = params.get("when", "upcoming")
        if when == "upcoming":
            queryset = queryset.filter(ends_at__gt=now, status=Event.Status.PUBLISHED).order_by(
                "starts_at"
            )
        elif when == "past":
            queryset = queryset.filter(ends_at__lte=now).order_by("-starts_at")
        else:
            queryset = queryset.order_by("-starts_at")
        for field in ("format", "kind"):
            if params.get(field):
                queryset = queryset.filter(**{field: params[field]})
        if params.get("community"):
            queryset = queryset.filter(community__slug=params["community"])
        if params.get("technology"):
            queryset = queryset.filter(technologies__slug=params["technology"]).distinct()
        return queryset

    def _respond(self, event: Event, status_code: int = status.HTTP_200_OK) -> Response:
        event = self.get_queryset().get(pk=event.pk)
        return Response(
            EventSerializer(event, context=self.get_serializer_context()).data, status=status_code
        )

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = EventWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = services.create_event(organizer=request.user, data=serializer.validated_data)
        return self._respond(event, status.HTTP_201_CREATED)

    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        event = self.get_object()
        serializer = EventWriteSerializer(event, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        services.update_event(event=event, actor=request.user, data=serializer.validated_data)
        return self._respond(event)

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        raise Http404

    @extend_schema(
        tags=TAG,
        summary="Annuler un événement",
        description="Organisateur uniquement ; les inscrits sont notifiés.",
        request=None,
        responses={200: EventSerializer, **errors(401, 403, 404, 409)},
    )
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def cancel(self, request: Request, pk: str | None = None) -> Response:
        return self._respond(services.cancel_event(event=self.get_object(), actor=request.user))

    @extend_schema(
        tags=TAG,
        summary="S'inscrire / se désinscrire",
        description="POST inscrit (idempotent, refusé si complet, annulé ou terminé) ; "
        "DELETE désinscrit.",
        request=None,
        responses={200: EventSerializer, **errors(401, 404, 409)},
    )
    @action(detail=True, methods=["post", "delete"], permission_classes=[IsAuthenticated])
    def register(self, request: Request, pk: str | None = None) -> Response:
        event = self.get_object()
        if request.method == "DELETE":
            services.unregister(event=event, user=request.user)
        else:
            services.register(event=event, user=request.user)
        return self._respond(event)

    @extend_schema(
        tags=TAG,
        summary="Inscrits",
        description="Réservé à l'organisateur.",
        responses={200: RegistrationSerializer(many=True), **errors(401, 403, 404)},
    )
    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated])
    def registrations(self, request: Request, pk: str | None = None) -> Response:
        event = self.get_object()
        if event.organizer_id != request.user.pk:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Réservé à l'organisateur.")
        queryset = event.registrations.filter(
            status=EventRegistration.Status.REGISTERED
        ).select_related("user__profile")
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(
            RegistrationSerializer(page, many=True, context=self.get_serializer_context()).data
        )

    @extend_schema(
        tags=TAG, summary="Mes inscriptions", responses={200: EventSerializer(many=True)}
    )
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def mine(self, request: Request) -> Response:
        page = self.paginate_queryset(self.get_queryset().order_by("starts_at"))
        return self.get_paginated_response(
            EventSerializer(page, many=True, context=self.get_serializer_context()).data
        )
