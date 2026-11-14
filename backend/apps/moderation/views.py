"""Endpoints des signalements (membres) et de la modération (modérateurs, admins)."""

from datetime import timedelta

from django.db.models import QuerySet
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.community.models import Answer, Comment, ContentStatus, Post
from apps.projects.models import Project
from common.permissions import IsAdmin, IsModerator
from common.schema import errors
from common.throttling import ActionThrottleMixin

from . import services
from .models import AuditLog, ModerationAction, Report
from .serializers import (
    ActionInputSerializer,
    AuditLogSerializer,
    DirectActionSerializer,
    ModerationActionSerializer,
    ModerationReportSerializer,
    MyReportSerializer,
    ReportCreateSerializer,
    StatsSerializer,
)

REPORT_TAG = ["Signalements"]
MOD_TAG = ["Modération"]


@extend_schema_view(
    create=extend_schema(
        tags=REPORT_TAG,
        summary="Signaler un contenu ou un profil",
        description="Réservé aux membres. Cibles : POST, COMMENT, ANSWER, PROFILE (id du compte), "
        "PROJECT. Impossible de signaler son propre contenu ou deux fois la même cible tant "
        "que le premier signalement est ouvert. Le motif OTHER exige des précisions.",
        request=ReportCreateSerializer,
        responses={201: MyReportSerializer, **errors(400, 401, 404, 409, 429)},
    ),
)
class ReportViewSet(ActionThrottleMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = MyReportSerializer
    action_throttle_scopes = {"create": "report_create"}

    def get_queryset(self) -> QuerySet[Report]:
        return Report.objects.filter(reporter=self.request.user).order_by("-created_at")

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = ReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report = services.create_report(reporter=request.user, **serializer.validated_data)
        return Response(MyReportSerializer(report).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=REPORT_TAG, summary="Mes signalements", responses={200: MyReportSerializer(many=True)}
    )
    @action(detail=False, methods=["get"])
    def mine(self, request: Request) -> Response:
        page = self.paginate_queryset(self.get_queryset())
        return self.get_paginated_response(MyReportSerializer(page, many=True).data)


@extend_schema_view(
    list=extend_schema(
        tags=MOD_TAG,
        summary="File des signalements",
        description="Réservé aux modérateurs et administrateurs. Par défaut : signalements ouverts "
        "(PENDING, REVIEWING), du plus ancien au plus récent.",
        parameters=[
            OpenApiParameter("status", str, enum=[*Report.Status.values, "ALL"]),
            OpenApiParameter("target_type", str),
            OpenApiParameter("reason", str, enum=Report.Reason.values),
        ],
    ),
    retrieve=extend_schema(
        tags=MOD_TAG,
        summary="Détail d'un signalement",
        responses={200: ModerationReportSerializer, **errors(401, 403, 404)},
    ),
)
class ModerationReportViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsModerator]
    serializer_class = ModerationReportSerializer

    def get_queryset(self) -> QuerySet[Report]:
        queryset = Report.objects.select_related("reporter", "assigned_to").prefetch_related(
            "actions__moderator"
        )
        if self.action != "list":
            return queryset
        params = self.request.query_params
        wanted = params.get("status")
        if wanted in Report.Status.values:
            queryset = queryset.filter(status=wanted)
        elif wanted != "ALL":
            queryset = queryset.filter(status__in=Report.OPEN_STATUSES)
        if params.get("target_type"):
            queryset = queryset.filter(target_type=params["target_type"])
        if params.get("reason"):
            queryset = queryset.filter(reason=params["reason"])
        return queryset.order_by("created_at")

    def _detail(self, report: Report) -> Response:
        report = self.get_queryset().get(pk=report.pk)
        return Response(
            ModerationReportSerializer(report, context=self.get_serializer_context()).data
        )

    @extend_schema(
        tags=MOD_TAG,
        summary="Prendre en charge un signalement",
        description="Passe le signalement en REVIEWING et l'assigne au modérateur. Impossible "
        "sur ses propres signalements.",
        request=None,
        responses={200: ModerationReportSerializer, **errors(401, 403, 404, 409)},
    )
    @action(detail=True, methods=["post"])
    def claim(self, request: Request, pk: str | None = None) -> Response:
        return self._detail(services.claim_report(report=self.get_object(), moderator=request.user))

    @extend_schema(
        tags=MOD_TAG,
        summary="Traiter un signalement",
        description="NO_ACTION rejette le signalement ; les autres actions le passent en "
        "ACTION_TAKEN. HIDE, DELETE, SUSPEND et BAN règlent aussi les autres signalements "
        "ouverts sur la même cible. BAN/UNBAN : administrateurs uniquement. Toute action est "
        "journalisée et le membre concerné est notifié (sans révéler le signaleur).",
        request=ActionInputSerializer,
        responses={200: ModerationReportSerializer, **errors(400, 401, 403, 404, 409)},
    )
    @action(detail=True, methods=["post"], url_path="action")
    def take_action(self, request: Request, pk: str | None = None) -> Response:
        report = self.get_object()
        serializer = ActionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.take_action(moderator=request.user, report=report, **serializer.validated_data)
        return self._detail(report)

    @extend_schema(
        tags=MOD_TAG,
        summary="Clôturer un signalement",
        description="Après une action ou un rejet.",
        request=None,
        responses={200: ModerationReportSerializer, **errors(401, 403, 404, 409)},
    )
    @action(detail=True, methods=["post"])
    def close(self, request: Request, pk: str | None = None) -> Response:
        return self._detail(services.close_report(report=self.get_object(), moderator=request.user))


@extend_schema_view(
    list=extend_schema(
        tags=MOD_TAG,
        summary="Historique des actions de modération",
        parameters=[OpenApiParameter("target_type", str), OpenApiParameter("target_id", str)],
    ),
    create=extend_schema(
        tags=MOD_TAG,
        summary="Action directe (sans signalement)",
        description="Ex. restaurer un contenu masqué par erreur (restaurer un contenu supprimé : "
        "administrateurs uniquement), lever une suspension.",
        request=DirectActionSerializer,
        responses={201: ModerationActionSerializer, **errors(400, 401, 403, 404, 409)},
    ),
)
class ModerationActionViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet
):
    permission_classes = [IsModerator]
    serializer_class = ModerationActionSerializer

    def get_queryset(self) -> QuerySet[ModerationAction]:
        queryset = ModerationAction.objects.select_related("moderator")
        params = self.request.query_params
        if params.get("target_type"):
            queryset = queryset.filter(target_type=params["target_type"])
        if params.get("target_id"):
            queryset = queryset.filter(target_id=params["target_id"])
        return queryset

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = DirectActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = services.take_action(moderator=request.user, **serializer.validated_data)
        return Response(ModerationActionSerializer(record).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    list=extend_schema(
        tags=MOD_TAG,
        summary="Journal d'audit",
        description="Réservé aux administrateurs.",
        parameters=[OpenApiParameter("action", str, description="Préfixe, ex. `moderation.`")],
    ),
)
class AuditLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAdmin]
    serializer_class = AuditLogSerializer

    def get_queryset(self) -> QuerySet[AuditLog]:
        queryset = AuditLog.objects.select_related("actor")
        prefix = self.request.query_params.get("action")
        return queryset.filter(action__startswith=prefix) if prefix else queryset


class ModerationStatsView(APIView):
    permission_classes = [IsModerator]

    @extend_schema(
        tags=MOD_TAG,
        summary="Statistiques simples",
        description="Réservé aux modérateurs et administrateurs.",
        responses={200: StatsSerializer, **errors(401, 403)},
    )
    def get(self, request: Request) -> Response:
        published = Post.all_objects.filter(status=ContentStatus.PUBLISHED)
        hidden = sum(
            model.all_objects.filter(status=ContentStatus.HIDDEN).count()
            for model in (Post, Comment, Answer)
        )
        return Response(
            {
                "members": User.objects.count(),
                "active_members": User.objects.filter(is_active=True).count(),
                "suspended_members": User.objects.filter(
                    suspended_until__gt=timezone.now()
                ).count(),
                "published_posts": published.count(),
                "questions": published.filter(type=Post.Type.QUESTION).count(),
                "answers": Answer.all_objects.filter(status=ContentStatus.PUBLISHED).count(),
                "projects": Project.objects.count(),
                "open_reports": Report.objects.filter(status__in=Report.OPEN_STATUSES).count(),
                "hidden_contents": hidden,
                "actions_last_30_days": ModerationAction.objects.filter(
                    created_at__gte=timezone.now() - timedelta(days=30)
                ).count(),
            }
        )
