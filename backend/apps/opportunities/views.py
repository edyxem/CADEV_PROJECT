"""Endpoints des opportunités et organisations."""

from django.db.models import Q, QuerySet
from django.http import Http404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.request import Request
from rest_framework.response import Response

from common.permissions import IsAdmin, IsModerator, is_moderator
from common.schema import errors
from common.throttling import ActionThrottleMixin

from . import services
from .models import Opportunity, Organization
from .serializers import (
    InterestSerializer,
    OpportunitySerializer,
    OpportunityWriteSerializer,
    OrganizationSerializer,
    ReviewSerializer,
    VerifySerializer,
)

TAG = ["Opportunités"]


def _base() -> QuerySet[Opportunity]:
    return Opportunity.objects.select_related(
        "publisher__profile", "organization", "country"
    ).prefetch_related("technologies")


@extend_schema_view(
    list=extend_schema(
        tags=TAG,
        summary="Annuaire des opportunités",
        description="Accès public. Annonces publiées et non expirées par défaut "
        "(`include_expired=true` pour les voir, signalées par `is_expired`).",
        parameters=[
            OpenApiParameter("type", str, enum=Opportunity.Type.values),
            OpenApiParameter("country", str),
            OpenApiParameter("work_mode", str, enum=Opportunity.WorkMode.values),
            OpenApiParameter("technology", str),
            OpenApiParameter("level", str),
            OpenApiParameter("include_expired", bool),
            OpenApiParameter("q", str),
        ],
    ),
    retrieve=extend_schema(
        tags=TAG,
        summary="Détail d'une opportunité",
        responses={200: OpportunitySerializer, **errors(404)},
    ),
    create=extend_schema(
        tags=TAG,
        summary="Publier une opportunité",
        description="Réservé aux membres. Source officielle obligatoire. Un membre d'organisation "
        "vérifiée publie directement ; sinon l'annonce attend la validation de la modération.",
        request=OpportunityWriteSerializer,
        responses={201: OpportunitySerializer, **errors(400, 401, 403, 429)},
    ),
    partial_update=extend_schema(
        tags=TAG,
        summary="Modifier son annonce",
        description="Une annonce publiée par un publieur non vérifié repasse en validation.",
        request=OpportunityWriteSerializer,
        responses={200: OpportunitySerializer, **errors(400, 401, 403, 404, 409)},
    ),
)
class OpportunityViewSet(ActionThrottleMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = OpportunitySerializer
    http_method_names = ["get", "post", "patch", "head", "options"]
    action_throttle_scopes = {"create": "content_create", "interests": "content_create"}

    def get_queryset(self) -> QuerySet[Opportunity]:
        if getattr(self, "swagger_fake_view", False):  # génération du schéma OpenAPI
            return Opportunity.objects.none()
        user = self.request.user
        if self.action == "list":
            return self._filtered(
                _base().filter(status=Opportunity.Status.PUBLISHED, hidden_by_moderation=False)
            )
        if self.action == "mine":
            return _base().filter(publisher=user)
        if self.action == "review_queue":
            return _base().filter(status=Opportunity.Status.PENDING_REVIEW)
        if is_moderator(user):
            return _base()
        visible = Q(status=Opportunity.Status.PUBLISHED, hidden_by_moderation=False)
        if user.is_authenticated:
            visible |= Q(publisher=user)
        return _base().filter(visible)

    def _filtered(self, queryset: QuerySet[Opportunity]) -> QuerySet[Opportunity]:
        params = self.request.query_params
        if params.get("include_expired") != "true":
            queryset = queryset.filter(
                Q(deadline__isnull=True) | Q(deadline__gte=timezone.localdate())
            )
        for field in ("type", "work_mode", "level"):
            if params.get(field):
                queryset = queryset.filter(**{field: params[field]})
        if params.get("country"):
            queryset = queryset.filter(country__code=params["country"].upper())
        if params.get("technology"):
            queryset = queryset.filter(technologies__slug=params["technology"].lower()).distinct()
        if params.get("q"):
            term = params["q"].strip()
            queryset = queryset.filter(
                Q(title__unaccent__icontains=term)
                | Q(description__unaccent__icontains=term)
                | Q(organization_name__unaccent__icontains=term)
                | Q(organization__name__unaccent__icontains=term)
            )
        return queryset

    def _respond(self, opportunity: Opportunity, status_code: int = status.HTTP_200_OK) -> Response:
        opportunity = _base().get(pk=opportunity.pk)
        return Response(
            OpportunitySerializer(opportunity, context=self.get_serializer_context()).data,
            status=status_code,
        )

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = OpportunityWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        submit = data.pop("submit")
        opportunity = services.create_opportunity(publisher=request.user, data=data, submit=submit)
        return self._respond(opportunity, status.HTTP_201_CREATED)

    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        opportunity = self.get_object()
        serializer = OpportunityWriteSerializer(opportunity, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        data.pop("submit", None)
        services.update_opportunity(opportunity=opportunity, actor=request.user, data=data)
        return self._respond(opportunity)

    @extend_schema(
        tags=TAG, summary="Mes annonces", responses={200: OpportunitySerializer(many=True)}
    )
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def mine(self, request: Request) -> Response:
        return super().list(request)

    @extend_schema(
        tags=TAG,
        summary="Soumettre un brouillon",
        request=None,
        responses={200: OpportunitySerializer, **errors(401, 403, 404, 409)},
    )
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def submit(self, request: Request, pk: str | None = None) -> Response:
        return self._respond(
            services.submit_opportunity(opportunity=self.get_object(), actor=request.user)
        )

    @extend_schema(
        tags=TAG,
        summary="File de validation des annonces",
        description="Réservé à la modération.",
        responses={200: OpportunitySerializer(many=True), **errors(401, 403)},
    )
    @action(
        detail=False, methods=["get"], url_path="review-queue", permission_classes=[IsModerator]
    )
    def review_queue(self, request: Request) -> Response:
        return super().list(request)

    @extend_schema(
        tags=TAG,
        summary="Valider ou refuser une annonce",
        description="Réservé à la modération ; journalisé ; le publieur est notifié.",
        request=ReviewSerializer,
        responses={200: OpportunitySerializer, **errors(400, 401, 403, 404, 409)},
    )
    @action(detail=True, methods=["post"], permission_classes=[IsModerator])
    def review(self, request: Request, pk: str | None = None) -> Response:
        serializer = ReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        opportunity = services.review_opportunity(
            opportunity=self.get_object(),
            moderator=request.user,
            approve=serializer.validated_data["approve"],
            note=serializer.validated_data.get("note", ""),
        )
        return self._respond(opportunity)

    @extend_schema(
        tags=TAG,
        summary="Candidater ou demander une information",
        description="GET : réservé au publieur. POST : membres, une demande par type ; refusé si "
        "l'annonce a expiré.",
        request=InterestSerializer,
        responses={
            200: InterestSerializer(many=True),
            201: InterestSerializer,
            **errors(400, 401, 403, 404, 409, 429),
        },
    )
    @action(detail=True, methods=["get", "post"], permission_classes=[IsAuthenticated])
    def interests(self, request: Request, pk: str | None = None) -> Response:
        opportunity = self.get_object()
        context = self.get_serializer_context()
        if request.method == "GET":
            if opportunity.publisher_id != request.user.pk:
                raise Http404
            queryset = opportunity.interests.select_related("user__profile")
            page = self.paginate_queryset(queryset)
            return self.get_paginated_response(
                InterestSerializer(page, many=True, context=context).data
            )
        serializer = InterestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        interest = services.express_interest(
            opportunity=opportunity, user=request.user, **serializer.validated_data
        )
        return Response(
            InterestSerializer(interest, context=context).data, status=status.HTTP_201_CREATED
        )


@extend_schema_view(
    list=extend_schema(tags=TAG, summary="Organisations"),
    retrieve=extend_schema(tags=TAG, summary="Détail d'une organisation"),
    create=extend_schema(
        tags=TAG,
        summary="Enregistrer une organisation",
        description="Le créateur en devient membre. La vérification est faite par "
        "un administrateur.",
        responses={201: OrganizationSerializer, **errors(400, 401)},
    ),
)
class OrganizationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = OrganizationSerializer
    queryset = Organization.objects.all()
    lookup_field = "slug"

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = OrganizationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization = services.create_organization(
            creator=request.user, data=serializer.validated_data
        )
        return Response(OrganizationSerializer(organization).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=TAG,
        summary="Vérifier une organisation",
        description="Réservé aux administrateurs ; journalisé.",
        request=VerifySerializer,
        responses={200: OrganizationSerializer, **errors(401, 403, 404)},
    )
    @action(detail=True, methods=["post"], permission_classes=[IsAdmin])
    def verify(self, request: Request, slug: str | None = None) -> Response:
        serializer = VerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization = services.verify_organization(
            organization=self.get_object(),
            actor=request.user,
            verified=serializer.validated_data["verified"],
        )
        return Response(OrganizationSerializer(organization).data)
