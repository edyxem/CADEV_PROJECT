"""Endpoints du mentorat."""

from django.db.models import Count, Q, QuerySet
from django.http import Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.schema import errors
from common.throttling import ActionThrottleMixin

from . import services
from .models import MentorProfile, MentorshipRequest, MentorshipSession
from .serializers import (
    FeedbackSerializer,
    MentorSerializer,
    MentorshipRequestCreateSerializer,
    MentorshipRequestSerializer,
    MentorWriteSerializer,
    RespondSerializer,
    SessionSerializer,
)

TAG = ["Mentorat"]


def _mentors() -> QuerySet[MentorProfile]:
    return (
        MentorProfile.objects.filter(user__is_active=True)
        .select_related("user__profile")
        .prefetch_related("domains", "technologies")
        .annotate(
            active_mentees=Count(
                "requests", filter=Q(requests__status=MentorshipRequest.Status.ACCEPTED)
            )
        )
    )


@extend_schema_view(
    list=extend_schema(
        tags=TAG,
        summary="Trouver un mentor",
        description="Accès public. Mentors disponibles ; filtres par domaine, technologie, langue.",
        parameters=[
            OpenApiParameter("domain", str),
            OpenApiParameter("technology", str),
            OpenApiParameter("language", str),
            OpenApiParameter("q", str),
        ],
    ),
    retrieve=extend_schema(tags=TAG, summary="Profil de mentor (par nom d'utilisateur)"),
)
class MentorViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = MentorSerializer
    lookup_field = "user__username"
    lookup_url_kwarg = "username"

    def get_queryset(self) -> QuerySet[MentorProfile]:
        queryset = _mentors()
        if self.action != "list":
            return queryset
        params = self.request.query_params
        queryset = queryset.filter(is_available=True)
        if params.get("domain"):
            queryset = queryset.filter(domains__slug=params["domain"])
        if params.get("technology"):
            queryset = queryset.filter(technologies__slug=params["technology"])
        if params.get("language"):
            queryset = queryset.filter(languages__contains=[params["language"]])
        if params.get("q"):
            queryset = queryset.filter(
                Q(headline__unaccent__icontains=params["q"])
                | Q(bio__unaccent__icontains=params["q"])
            )
        return queryset.distinct().order_by("-created_at")


class MyMentorProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=TAG,
        summary="Mon profil de mentor",
        responses={200: MentorSerializer, **errors(401, 404)},
    )
    def get(self, request: Request) -> Response:
        profile = get_object_or_404(_mentors(), user=request.user)
        return Response(MentorSerializer(profile, context={"request": request}).data)

    @extend_schema(
        tags=TAG,
        summary="Devenir mentor / modifier mon profil de mentor",
        description="Déclaration volontaire ; `is_available=false` suspend les nouvelles demandes.",
        request=MentorWriteSerializer,
        responses={200: MentorSerializer, **errors(400, 401)},
    )
    def put(self, request: Request) -> Response:
        instance = MentorProfile.objects.filter(user=request.user).first()
        serializer = MentorWriteSerializer(
            instance, data=request.data, partial=instance is not None
        )
        serializer.is_valid(raise_exception=True)
        services.save_mentor_profile(user=request.user, data=serializer.validated_data)
        return self.get(request)


@extend_schema_view(
    list=extend_schema(
        tags=TAG,
        summary="Mes demandes de mentorat",
        description="Demandes envoyées (`role=mentee`) ou reçues (`role=mentor`).",
        parameters=[OpenApiParameter("role", str, enum=["mentee", "mentor"])],
    ),
    retrieve=extend_schema(
        tags=TAG,
        summary="Détail d'une demande",
        responses={200: MentorshipRequestSerializer, **errors(401, 404)},
    ),
    create=extend_schema(
        tags=TAG,
        summary="Demander un mentorat",
        description="Objectif explicite obligatoire (30 caractères minimum). "
        "Jamais accepté automatiquement.",
        request=MentorshipRequestCreateSerializer,
        responses={201: MentorshipRequestSerializer, **errors(400, 401, 409, 429)},
    ),
)
class MentorshipRequestViewSet(
    ActionThrottleMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    serializer_class = MentorshipRequestSerializer
    action_throttle_scopes = {"create": "content_create"}

    def get_queryset(self) -> QuerySet[MentorshipRequest]:
        if getattr(self, "swagger_fake_view", False):  # génération du schéma OpenAPI
            return MentorshipRequest.objects.none()
        user = self.request.user
        queryset = MentorshipRequest.objects.select_related(
            "mentee__profile", "mentor__user__profile"
        )
        role = self.request.query_params.get("role")
        if self.action == "list" and role == "mentee":
            return queryset.filter(mentee=user)
        if self.action == "list" and role == "mentor":
            return queryset.filter(mentor__user=user)
        # Visible des seuls participants (§M, confidentialité).
        return queryset.filter(Q(mentee=user) | Q(mentor__user=user))

    def _respond(self, request_obj: MentorshipRequest) -> Response:
        request_obj.refresh_from_db()
        return Response(
            MentorshipRequestSerializer(request_obj, context=self.get_serializer_context()).data
        )

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = MentorshipRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mentorship = services.request_mentorship(
            mentee=request.user,
            mentor=serializer.validated_data["mentor"].mentor_profile,
            goal=serializer.validated_data["goal"],
        )
        return Response(
            MentorshipRequestSerializer(mentorship, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        tags=TAG,
        summary="Répondre à une demande (mentor)",
        description="Refusé si la capacité d'accompagnement est atteinte.",
        request=RespondSerializer,
        responses={200: MentorshipRequestSerializer, **errors(400, 401, 403, 404, 409)},
    )
    @action(detail=True, methods=["post"])
    def respond(self, request: Request, pk: str | None = None) -> Response:
        serializer = RespondSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mentorship = self.get_object()
        services.respond(request=mentorship, mentor_user=request.user, **serializer.validated_data)
        return self._respond(mentorship)

    @extend_schema(
        tags=TAG,
        summary="Annuler",
        request=None,
        responses={200: MentorshipRequestSerializer, **errors(401, 404, 409)},
    )
    @action(detail=True, methods=["post"])
    def cancel(self, request: Request, pk: str | None = None) -> Response:
        mentorship = self.get_object()
        services.cancel(request=mentorship, actor=request.user)
        return self._respond(mentorship)

    @extend_schema(
        tags=TAG,
        summary="Marquer le mentorat comme terminé",
        request=None,
        responses={200: MentorshipRequestSerializer, **errors(401, 404, 409)},
    )
    @action(detail=True, methods=["post"])
    def complete(self, request: Request, pk: str | None = None) -> Response:
        mentorship = self.get_object()
        services.complete(request=mentorship, actor=request.user)
        return self._respond(mentorship)

    @extend_schema(
        tags=TAG,
        summary="Sessions du mentorat",
        description="Participants uniquement ; le lien de réunion n'est visible que d'eux.",
        request=SessionSerializer,
        responses={
            200: SessionSerializer(many=True),
            201: SessionSerializer,
            **errors(400, 401, 404, 409),
        },
    )
    @action(detail=True, methods=["get", "post"])
    def sessions(self, request: Request, pk: str | None = None) -> Response:
        mentorship = self.get_object()
        if request.method == "GET":
            return Response(SessionSerializer(mentorship.sessions.all(), many=True).data)
        serializer = SessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = services.plan_session(
            request=mentorship, actor=request.user, data=serializer.validated_data
        )
        return Response(SessionSerializer(session).data, status=status.HTTP_201_CREATED)


class SessionViewSet(mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = SessionSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self) -> QuerySet[MentorshipSession]:
        if getattr(self, "swagger_fake_view", False):  # génération du schéma OpenAPI
            return MentorshipSession.objects.none()
        user = self.request.user
        return MentorshipSession.objects.select_related("request__mentor").filter(
            Q(request__mentee=user) | Q(request__mentor__user=user)
        )

    @extend_schema(
        tags=TAG,
        summary="Modifier ou terminer une session",
        request=SessionSerializer,
        responses={200: SessionSerializer, **errors(400, 401, 404, 409)},
    )
    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        session = self.get_object()
        serializer = SessionSerializer(session, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        session = services.update_session(
            session=session, actor=request.user, data=serializer.validated_data
        )
        return Response(SessionSerializer(session).data)

    @extend_schema(
        tags=TAG,
        summary="Retours sur une session",
        description="Après une session terminée ; un retour par participant ; "
        "visibles des seuls participants.",
        request=FeedbackSerializer,
        responses={
            200: FeedbackSerializer(many=True),
            201: FeedbackSerializer,
            **errors(400, 401, 404, 409),
        },
    )
    @action(detail=True, methods=["get", "post"])
    def feedback(self, request: Request, pk: str | None = None) -> Response:
        session = self.get_object()
        context = self.get_serializer_context()
        if request.method == "GET":
            return Response(
                FeedbackSerializer(
                    session.feedbacks.select_related("author__profile"), many=True, context=context
                ).data
            )
        serializer = FeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        feedback = services.leave_feedback(
            session=session, author=request.user, **serializer.validated_data
        )
        return Response(
            FeedbackSerializer(feedback, context=context).data, status=status.HTTP_201_CREATED
        )

    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        session = self.get_object()
        if session is None:  # pragma: no cover
            raise Http404
        return Response(SessionSerializer(session).data)
