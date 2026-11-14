"""Endpoints des projets collaboratifs."""

import uuid

from django.db.models import QuerySet
from django.http import Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.request import Request
from rest_framework.response import Response

from apps.profiles.serializers import AvatarSerializer
from common.permissions import is_moderator
from common.schema import errors
from common.throttling import ActionThrottleMixin

from . import policies, selectors, services
from .filters import ProjectFilter
from .models import (
    JoinRequest,
    Milestone,
    Project,
    ProjectInvitation,
    ProjectMember,
    ProjectRoleNeed,
    ProjectTask,
)
from .serializers import (
    ActivitySerializer,
    InvitationCreateSerializer,
    InvitationSerializer,
    JoinRequestCreateSerializer,
    JoinRequestDecisionSerializer,
    JoinRequestSerializer,
    MemberSerializer,
    MemberUpdateSerializer,
    MilestoneSerializer,
    ProjectDetailSerializer,
    ProjectListSerializer,
    ProjectUpdateSerializer,
    ProjectWriteSerializer,
    RoleNeedSerializer,
    RoleNeedWriteSerializer,
    TaskCommentSerializer,
    TaskSerializer,
    TaskWriteSerializer,
    TransferOwnershipSerializer,
)

TAG = ["Projets"]
TEAM_TAG = ["Projets — équipe et demandes"]
TASK_TAG = ["Projets — tâches"]
UUID_RE = "[0-9a-f-]{36}"


def _member_or_404(project: Project, member_id: str) -> ProjectMember:
    return get_object_or_404(
        ProjectMember, pk=member_id, project=project, status=ProjectMember.Status.ACTIVE
    )


@extend_schema_view(
    list=extend_schema(
        tags=TAG,
        summary="Lister les projets publics",
        description="Accès public. Projets publics non archivés ; `recruiting=true` pour ceux qui "
        "acceptent des membres.",
    ),
    retrieve=extend_schema(
        tags=TAG,
        summary="Détail d'un projet (slug ou identifiant)",
        description="Accès public pour un projet public ; un projet privé n'est visible que de ses "
        "membres. `permissions` indique ce que le lecteur peut faire.",
        responses={200: ProjectDetailSerializer, **errors(404)},
    ),
    create=extend_schema(
        tags=TAG,
        summary="Créer un projet / appel à collaboration",
        description="Réservé aux membres connectés. Le créateur devient propriétaire.",
        request=ProjectWriteSerializer,
        responses={201: ProjectDetailSerializer, **errors(400, 401, 429)},
    ),
    partial_update=extend_schema(
        tags=TAG,
        summary="Modifier un projet",
        description="Réservé au propriétaire. Les changements de `status` suivent la table des "
        "transitions ; les membres sont notifiés.",
        request=ProjectWriteSerializer,
        responses={200: ProjectDetailSerializer, **errors(400, 401, 403, 404, 409)},
    ),
)
class ProjectViewSet(ActionThrottleMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    filterset_class = ProjectFilter
    lookup_field = "slug"
    lookup_value_regex = r"[\w-]+"
    http_method_names = ["get", "post", "patch", "put", "delete", "head", "options"]
    action_throttle_scopes = {"create": "content_create", "join_requests": "join_request"}

    def get_queryset(self) -> QuerySet[Project]:
        if getattr(self, "swagger_fake_view", False):  # génération du schéma OpenAPI
            return Project.objects.none()
        if self.action == "list":
            return selectors.public_projects().order_by("-created_at")
        if self.action == "mine":
            return selectors.my_projects(self.request.user).order_by("-created_at")
        return selectors.visible_projects(self.request.user)

    def get_serializer_class(self):
        if self.action in {"list", "mine"}:
            return ProjectListSerializer
        if self.action in {"create", "partial_update"}:
            return ProjectWriteSerializer
        return ProjectDetailSerializer

    def get_object(self) -> Project:
        value = self.kwargs["slug"]
        try:
            lookup = {"pk": uuid.UUID(value)}
        except ValueError:
            lookup = {"slug": value}
        project = get_object_or_404(self.get_queryset(), **lookup)
        policies.ensure_can_view(project, self.request.user)
        return project

    def _detail(self, project: Project, status_code: int = status.HTTP_200_OK) -> Response:
        project = selectors.visible_projects(self.request.user).get(pk=project.pk)
        data = ProjectDetailSerializer(project, context=self.get_serializer_context()).data
        return Response(data, status=status_code)

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = ProjectWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = services.create_project(owner=request.user, data=serializer.validated_data)
        return self._detail(project, status.HTTP_201_CREATED)

    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        project = self.get_object()
        serializer = ProjectWriteSerializer(project, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        services.update_project(project=project, actor=request.user, data=serializer.validated_data)
        return self._detail(project)

    def update(self, request: Request, *args, **kwargs) -> Response:
        raise Http404

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        raise Http404

    @extend_schema(
        tags=TAG,
        summary="Mes projets",
        description="Projets dont le membre connecté fait activement partie.",
        responses={200: ProjectListSerializer(many=True), **errors(401)},
    )
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def mine(self, request: Request) -> Response:
        return super().list(request)

    @extend_schema(
        tags=TAG,
        summary="Logo du projet",
        description="Réservé au propriétaire. Mêmes contrôles que l'avatar (JPEG, PNG, WebP).",
        request={"multipart/form-data": AvatarSerializer},
        responses={200: ProjectDetailSerializer, 204: None, **errors(400, 401, 403)},
    )
    @action(
        detail=True,
        methods=["put", "delete"],
        parser_classes=[MultiPartParser],
        permission_classes=[IsAuthenticated],
    )
    def logo(self, request: Request, slug: str | None = None) -> Response:
        project = self.get_object()
        if request.method == "DELETE":
            services.remove_logo(project=project, actor=request.user)
            return Response(status=status.HTTP_204_NO_CONTENT)
        upload = request.data.get("logo") or request.data.get("avatar")
        if upload is None:
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"logo": ["Fichier image requis."]})
        services.update_logo(project=project, actor=request.user, upload=upload)
        return self._detail(project)

    # --- Équipe ---------------------------------------------------------------------

    @extend_schema(
        tags=TEAM_TAG,
        summary="Membres du projet",
        description="Visible de quiconque peut voir le projet.",
        responses={200: MemberSerializer(many=True), **errors(404)},
    )
    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticatedOrReadOnly])
    def members(self, request: Request, slug: str | None = None) -> Response:
        project = self.get_object()
        page = self.paginate_queryset(selectors.active_members(project))
        data = MemberSerializer(page, many=True, context=self.get_serializer_context()).data
        return self.get_paginated_response(data)

    @extend_schema(
        tags=TEAM_TAG,
        summary="Modifier ou retirer un membre",
        description="Propriétaire, ou responsable habilité pour les contributeurs et observateurs. "
        "Le propriétaire ne peut être ni modifié ni retiré.",
        request=MemberUpdateSerializer,
        responses={200: MemberSerializer, 204: None, **errors(400, 401, 403, 404)},
    )
    @action(
        detail=True,
        methods=["patch", "delete"],
        url_path=f"members/(?P<member_id>{UUID_RE})",
        permission_classes=[IsAuthenticated],
    )
    def member_detail(
        self, request: Request, slug: str | None = None, member_id: str | None = None
    ) -> Response:
        project = self.get_object()
        member = _member_or_404(project, member_id)
        if request.method == "DELETE":
            services.remove_member(member=member, actor=request.user)
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = MemberUpdateSerializer(member, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        member = services.update_member(
            member=member, actor=request.user, data=serializer.validated_data
        )
        return Response(MemberSerializer(member, context=self.get_serializer_context()).data)

    @extend_schema(
        tags=TEAM_TAG,
        summary="Quitter le projet",
        description="Tout membre sauf le propriétaire, qui doit d'abord transférer la propriété.",
        request=None,
        responses={204: None, **errors(401, 404, 409)},
    )
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def leave(self, request: Request, slug: str | None = None) -> Response:
        services.leave_project(project=self.get_object(), user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        tags=TEAM_TAG,
        summary="Transférer la propriété",
        description="Réservé au propriétaire, vers un membre actif non observateur. L'ancien "
        "propriétaire devient responsable habilité.",
        request=TransferOwnershipSerializer,
        responses={200: ProjectDetailSerializer, **errors(400, 401, 403, 409)},
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="transfer-ownership",
        permission_classes=[IsAuthenticated],
    )
    def transfer_ownership(self, request: Request, slug: str | None = None) -> Response:
        project = self.get_object()
        serializer = TransferOwnershipSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.transfer_ownership(
            project=project, actor=request.user, new_owner=serializer.validated_data["username"]
        )
        return self._detail(project)

    @extend_schema(
        tags=TEAM_TAG,
        summary="Demandes pour rejoindre",
        description="GET : propriétaire et responsables habilités uniquement (les autres "
        "membres ne voient pas les candidatures). POST : membre connecté non membre, message "
        "motivé (20 caractères minimum), une seule demande en attente par projet.",
        parameters=[OpenApiParameter("status", str, enum=JoinRequest.Status.values)],
        request=JoinRequestCreateSerializer,
        responses={
            200: JoinRequestSerializer(many=True),
            201: JoinRequestSerializer,
            **errors(400, 401, 403, 404, 409, 429),
        },
    )
    @action(
        detail=True,
        methods=["get", "post"],
        url_path="join-requests",
        permission_classes=[IsAuthenticated],
    )
    def join_requests(self, request: Request, slug: str | None = None) -> Response:
        project = self.get_object()
        context = self.get_serializer_context()
        if request.method == "GET":
            if not policies.can_manage_members(project, request.user):
                from rest_framework.exceptions import PermissionDenied

                raise PermissionDenied("Réservé au propriétaire et aux responsables habilités.")
            queryset = selectors.project_join_requests(project)
            if request.query_params.get("status") in JoinRequest.Status.values:
                queryset = queryset.filter(status=request.query_params["status"])
            page = self.paginate_queryset(queryset)
            return self.get_paginated_response(
                JoinRequestSerializer(page, many=True, context=context).data
            )

        serializer = JoinRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role_id = serializer.validated_data.get("requested_role")
        role = get_object_or_404(ProjectRoleNeed, pk=role_id, project=project) if role_id else None
        join_request = services.create_join_request(
            project=project,
            user=request.user,
            message=serializer.validated_data["message"],
            requested_role=role,
        )
        return Response(
            JoinRequestSerializer(join_request, context=context).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        tags=TEAM_TAG,
        summary="Rôles recherchés",
        description="GET public ; POST réservé au propriétaire et aux responsables habilités.",
        request=RoleNeedWriteSerializer,
        responses={
            200: RoleNeedSerializer(many=True),
            201: RoleNeedSerializer,
            **errors(400, 401, 403, 404),
        },
    )
    @action(detail=True, methods=["get", "post"], permission_classes=[IsAuthenticatedOrReadOnly])
    def roles(self, request: Request, slug: str | None = None) -> Response:
        project = self.get_object()
        if request.method == "GET":
            queryset = project.role_needs.prefetch_related("required_technologies")
            return Response(RoleNeedSerializer(queryset, many=True).data)
        serializer = RoleNeedWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = services.save_role_need(
            project=project, actor=request.user, data=serializer.validated_data
        )
        return Response(RoleNeedSerializer(role).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=TEAM_TAG,
        summary="Modifier ou supprimer un rôle recherché",
        request=RoleNeedWriteSerializer,
        responses={200: RoleNeedSerializer, 204: None, **errors(400, 401, 403, 404)},
    )
    @action(
        detail=True,
        methods=["patch", "delete"],
        url_path=f"roles/(?P<role_id>{UUID_RE})",
        permission_classes=[IsAuthenticated],
    )
    def role_detail(
        self, request: Request, slug: str | None = None, role_id: str | None = None
    ) -> Response:
        project = self.get_object()
        role = get_object_or_404(ProjectRoleNeed, pk=role_id, project=project)
        if request.method == "DELETE":
            services.delete_role_need(role_need=role, actor=request.user)
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = RoleNeedWriteSerializer(role, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        role = services.save_role_need(
            project=project, actor=request.user, data=serializer.validated_data, instance=role
        )
        return Response(RoleNeedSerializer(role).data)

    # --- Suivi avancé (P1) -----------------------------------------------------------

    def _require(self, allowed: bool, message: str) -> None:
        if not allowed:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied(message)

    @extend_schema(
        tags=TASK_TAG,
        summary="Jalons du projet",
        description="GET : quiconque voit le projet. POST : propriétaire et responsables.",
        request=MilestoneSerializer,
        responses={
            200: MilestoneSerializer(many=True),
            201: MilestoneSerializer,
            **errors(400, 401, 403, 404),
        },
    )
    @action(detail=True, methods=["get", "post"], permission_classes=[IsAuthenticatedOrReadOnly])
    def milestones(self, request: Request, slug: str | None = None) -> Response:
        project = self.get_object()
        if request.method == "GET":
            return Response(MilestoneSerializer(project.milestones.all(), many=True).data)
        serializer = MilestoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        milestone = services.save_milestone(
            project=project, actor=request.user, data=serializer.validated_data
        )
        return Response(MilestoneSerializer(milestone).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=TASK_TAG,
        summary="Modifier ou supprimer un jalon",
        description="`status=COMPLETED` marque le jalon comme atteint.",
        request=MilestoneSerializer,
        responses={200: MilestoneSerializer, 204: None, **errors(400, 401, 403, 404)},
    )
    @action(
        detail=True,
        methods=["patch", "delete"],
        url_path=f"milestones/(?P<milestone_id>{UUID_RE})",
        permission_classes=[IsAuthenticated],
    )
    def milestone_detail(
        self, request: Request, slug: str | None = None, milestone_id: str | None = None
    ) -> Response:
        project = self.get_object()
        milestone = get_object_or_404(Milestone, pk=milestone_id, project=project)
        if request.method == "DELETE":
            services.delete_milestone(milestone=milestone, actor=request.user)
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = MilestoneSerializer(milestone, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        milestone = services.save_milestone(
            project=project, actor=request.user, data=serializer.validated_data, instance=milestone
        )
        return Response(MilestoneSerializer(milestone).data)

    @extend_schema(
        tags=TAG,
        summary="Mises à jour du projet",
        description="GET : quiconque voit le projet. POST : propriétaire et responsables ; les "
        "membres sont notifiés.",
        request=ProjectUpdateSerializer,
        responses={
            200: ProjectUpdateSerializer(many=True),
            201: ProjectUpdateSerializer,
            **errors(400, 401, 403, 404),
        },
    )
    @action(detail=True, methods=["get", "post"], permission_classes=[IsAuthenticatedOrReadOnly])
    def updates(self, request: Request, slug: str | None = None) -> Response:
        project = self.get_object()
        context = self.get_serializer_context()
        if request.method == "GET":
            page = self.paginate_queryset(project.updates.select_related("author__profile"))
            return self.get_paginated_response(
                ProjectUpdateSerializer(page, many=True, context=context).data
            )
        serializer = ProjectUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        update = services.publish_update(
            project=project, actor=request.user, **serializer.validated_data
        )
        return Response(
            ProjectUpdateSerializer(update, context=context).data, status=status.HTTP_201_CREATED
        )

    @extend_schema(
        tags=TAG,
        summary="Fil d'activité et historique",
        description="Réservé aux membres du projet (et à la modération).",
        responses={200: ActivitySerializer(many=True), **errors(401, 403, 404)},
    )
    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated])
    def activity(self, request: Request, slug: str | None = None) -> Response:
        project = self.get_object()
        self._require(
            policies.can_view_tasks(project, request.user), "Réservé aux membres du projet."
        )
        page = self.paginate_queryset(project.activities.select_related("actor__profile"))
        return self.get_paginated_response(
            ActivitySerializer(page, many=True, context=self.get_serializer_context()).data
        )

    @extend_schema(
        tags=TASK_TAG,
        summary="Tableau Kanban",
        description="Tâches regroupées par statut (une colonne par statut). Réservé aux membres.",
        responses={200: TaskSerializer(many=True), **errors(401, 403, 404)},
    )
    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated])
    def board(self, request: Request, slug: str | None = None) -> Response:
        project = self.get_object()
        self._require(
            policies.can_view_tasks(project, request.user), "Réservé aux membres du projet."
        )
        context = self.get_serializer_context()
        columns = {value: [] for value in ProjectTask.Status.values}
        for task in selectors.project_tasks(project):
            columns[task.status].append(TaskSerializer(task, context=context).data)
        labels = dict(ProjectTask.Status.choices)
        return Response(
            [
                {"status": value, "label": labels[value], "tasks": tasks}
                for value, tasks in columns.items()
            ]
        )

    @extend_schema(
        tags=TEAM_TAG,
        summary="Invitations du projet",
        description="Propriétaire et responsables habilités : lister et inviter directement un "
        "membre (le rôle MANAGER est réservé au propriétaire).",
        request=InvitationCreateSerializer,
        responses={
            200: InvitationSerializer(many=True),
            201: InvitationSerializer,
            **errors(400, 401, 403, 404, 409),
        },
    )
    @action(detail=True, methods=["get", "post"], permission_classes=[IsAuthenticated])
    def invitations(self, request: Request, slug: str | None = None) -> Response:
        project = self.get_object()
        context = self.get_serializer_context()
        self._require(
            policies.can_manage_members(project, request.user),
            "Réservé au propriétaire et aux responsables habilités.",
        )
        if request.method == "GET":
            queryset = project.invitations.select_related(
                "invitee__profile", "invited_by__profile", "project"
            )
            page = self.paginate_queryset(queryset)
            return self.get_paginated_response(
                InvitationSerializer(page, many=True, context=context).data
            )
        serializer = InvitationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        invitation = services.invite(
            project=project,
            actor=request.user,
            invitee=data["username"],
            role=data["role"],
            message=data.get("message", ""),
        )
        return Response(
            InvitationSerializer(invitation, context=context).data, status=status.HTTP_201_CREATED
        )

    # --- Tâches ---------------------------------------------------------------------

    @extend_schema(
        tags=TASK_TAG,
        summary="Tâches du projet",
        description="Réservé aux membres du projet. POST : propriétaire, responsables et "
        "contributeurs ; un contributeur ne s'assigne que lui-même ; l'assigné doit être un membre "
        "actif non observateur.",
        parameters=[
            OpenApiParameter("status", str, enum=ProjectTask.Status.values),
            OpenApiParameter("assignee", str, description="Nom d'utilisateur, ou `me`."),
        ],
        request=TaskWriteSerializer,
        responses={
            200: TaskSerializer(many=True),
            201: TaskSerializer,
            **errors(400, 401, 403, 404, 409),
        },
    )
    @action(detail=True, methods=["get", "post"], permission_classes=[IsAuthenticated])
    def tasks(self, request: Request, slug: str | None = None) -> Response:
        project = self.get_object()
        context = self.get_serializer_context()
        if not policies.can_view_tasks(project, request.user):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Réservé aux membres du projet.")
        if request.method == "GET":
            queryset = selectors.project_tasks(project)
            if request.query_params.get("status") in ProjectTask.Status.values:
                queryset = queryset.filter(status=request.query_params["status"])
            assignee = request.query_params.get("assignee")
            if assignee == "me":
                queryset = queryset.filter(assignee=request.user)
            elif assignee:
                queryset = queryset.filter(assignee__username__iexact=assignee)
            page = self.paginate_queryset(queryset)
            return self.get_paginated_response(
                TaskSerializer(page, many=True, context=context).data
            )

        serializer = TaskWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = services.create_task(
            project=project, actor=request.user, data=serializer.validated_data
        )
        return Response(TaskSerializer(task, context=context).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    retrieve=extend_schema(
        tags=TEAM_TAG,
        summary="Consulter une demande",
        description="Visible du candidat et des gestionnaires du projet uniquement.",
        responses={200: JoinRequestSerializer, **errors(401, 404)},
    ),
)
class JoinRequestViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = JoinRequestSerializer

    def get_queryset(self) -> QuerySet[JoinRequest]:
        return JoinRequest.objects.select_related("project", "user__profile", "requested_role")

    def get_object(self) -> JoinRequest:
        join_request = super().get_object()
        user = self.request.user
        allowed = join_request.user_id == user.pk or policies.can_manage_members(
            join_request.project, user
        )
        if not allowed and not is_moderator(user):
            raise Http404
        return join_request

    def _respond(self, join_request: JoinRequest) -> Response:
        join_request.refresh_from_db()
        return Response(
            JoinRequestSerializer(join_request, context=self.get_serializer_context()).data
        )

    @extend_schema(
        tags=TEAM_TAG,
        summary="Mes demandes envoyées",
        responses={200: JoinRequestSerializer(many=True), **errors(401)},
    )
    @action(detail=False, methods=["get"])
    def mine(self, request: Request) -> Response:
        page = self.paginate_queryset(
            self.get_queryset().filter(user=request.user).order_by("-created_at")
        )
        return self.get_paginated_response(
            JoinRequestSerializer(page, many=True, context=self.get_serializer_context()).data
        )

    @extend_schema(
        tags=TEAM_TAG,
        summary="Accepter une demande",
        description="Propriétaire ou responsable habilité. Crée le membre dans la même transaction "
        "et notifie le candidat. Refusé si le projet est fermé, suspendu, terminé ou archivé.",
        request=JoinRequestDecisionSerializer,
        responses={200: JoinRequestSerializer, **errors(400, 401, 403, 404, 409)},
    )
    @action(detail=True, methods=["post"])
    def accept(self, request: Request, pk: str | None = None) -> Response:
        join_request = self.get_object()
        serializer = JoinRequestDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.accept_join_request(
            join_request=join_request,
            actor=request.user,
            role=serializer.validated_data["role"],
            response=serializer.validated_data.get("response_message", ""),
        )
        return self._respond(join_request)

    @extend_schema(
        tags=TEAM_TAG,
        summary="Refuser une demande",
        description="Propriétaire ou responsable habilité. Le candidat ne peut pas redemander "
        "avant 30 jours, sauf autorisation explicite (`allow-reapply`).",
        request=JoinRequestDecisionSerializer,
        responses={200: JoinRequestSerializer, **errors(401, 403, 404, 409)},
    )
    @action(detail=True, methods=["post"])
    def reject(self, request: Request, pk: str | None = None) -> Response:
        join_request = self.get_object()
        serializer = JoinRequestDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.reject_join_request(
            join_request=join_request,
            actor=request.user,
            response=serializer.validated_data.get("response_message", ""),
        )
        return self._respond(join_request)

    @extend_schema(
        tags=TEAM_TAG,
        summary="Retirer sa demande",
        description="Réservé au candidat, tant que la demande est en attente.",
        request=None,
        responses={200: JoinRequestSerializer, **errors(401, 403, 404, 409)},
    )
    @action(detail=True, methods=["post"])
    def withdraw(self, request: Request, pk: str | None = None) -> Response:
        join_request = self.get_object()
        services.withdraw_join_request(join_request=join_request, actor=request.user)
        return self._respond(join_request)

    @extend_schema(
        tags=TEAM_TAG,
        summary="Autoriser une nouvelle demande",
        description="Après un refus, permet au candidat de redemander sans attendre.",
        request=None,
        responses={200: JoinRequestSerializer, **errors(401, 403, 404, 409)},
    )
    @action(detail=True, methods=["post"], url_path="allow-reapply")
    def allow_reapply(self, request: Request, pk: str | None = None) -> Response:
        join_request = self.get_object()
        services.allow_reapply(join_request=join_request, actor=request.user)
        return self._respond(join_request)


@extend_schema_view(
    retrieve=extend_schema(
        tags=TASK_TAG,
        summary="Consulter une tâche",
        responses={200: TaskSerializer, **errors(401, 404)},
    ),
    partial_update=extend_schema(
        tags=TASK_TAG,
        summary="Modifier une tâche",
        description="Propriétaire et responsables : toutes les tâches. Contributeur : celles qu'il "
        "a créées ou qui lui sont assignées. Observateur : lecture seule. Terminer une tâche est "
        "réservé à l'assigné et aux gestionnaires ; la rouvrir aux gestionnaires.",
        request=TaskWriteSerializer,
        responses={200: TaskSerializer, **errors(400, 401, 403, 404, 409)},
    ),
    destroy=extend_schema(
        tags=TASK_TAG,
        summary="Supprimer une tâche",
        description="Propriétaire et responsables ; une tâche terminée est conservée.",
        responses={204: None, **errors(401, 403, 404, 409)},
    ),
)
class TaskViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    serializer_class = TaskSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self) -> QuerySet[ProjectTask]:
        if getattr(self, "swagger_fake_view", False):  # génération du schéma OpenAPI
            return ProjectTask.objects.none()
        # Seules les tâches des projets dont le lecteur est membre existent pour lui (IDOR → 404).
        queryset = ProjectTask.objects.select_related(
            "project", "assignee__profile", "created_by__profile"
        )
        if is_moderator(self.request.user):
            return queryset
        return queryset.filter(
            project__memberships__user=self.request.user,
            project__memberships__status=ProjectMember.Status.ACTIVE,
        )

    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        task = self.get_object()
        serializer = TaskWriteSerializer(task, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        task = services.update_task(task=task, actor=request.user, data=serializer.validated_data)
        return Response(TaskSerializer(task, context=self.get_serializer_context()).data)

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        services.delete_task(task=self.get_object(), actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        tags=TASK_TAG,
        summary="Commentaires d'une tâche",
        description="Membres du projet ; les observateurs lisent sans commenter.",
        request=TaskCommentSerializer,
        responses={
            200: TaskCommentSerializer(many=True),
            201: TaskCommentSerializer,
            **errors(400, 401, 403, 404),
        },
    )
    @action(detail=True, methods=["get", "post"])
    def comments(self, request: Request, pk: str | None = None) -> Response:
        task = self.get_object()
        context = self.get_serializer_context()
        if request.method == "GET":
            queryset = task.comments.select_related("author__profile")
            return Response(TaskCommentSerializer(queryset, many=True, context=context).data)
        serializer = TaskCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = services.add_task_comment(
            task=task, actor=request.user, content=serializer.validated_data["content"]
        )
        return Response(
            TaskCommentSerializer(comment, context=context).data, status=status.HTTP_201_CREATED
        )


@extend_schema_view(
    retrieve=extend_schema(
        tags=TEAM_TAG,
        summary="Consulter une invitation",
        responses={200: InvitationSerializer, **errors(401, 404)},
    ),
)
class InvitationViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = InvitationSerializer

    def get_queryset(self) -> QuerySet[ProjectInvitation]:
        if getattr(self, "swagger_fake_view", False):  # génération du schéma OpenAPI
            return ProjectInvitation.objects.none()
        return ProjectInvitation.objects.select_related(
            "project", "invitee__profile", "invited_by__profile"
        )

    def get_object(self) -> ProjectInvitation:
        invitation = super().get_object()
        user = self.request.user
        if invitation.invitee_id != user.pk and not policies.can_manage_members(
            invitation.project, user
        ):
            raise Http404
        return invitation

    def _respond(self, invitation: ProjectInvitation) -> Response:
        invitation.refresh_from_db()
        return Response(
            InvitationSerializer(invitation, context=self.get_serializer_context()).data
        )

    @extend_schema(
        tags=TEAM_TAG,
        summary="Mes invitations reçues",
        responses={200: InvitationSerializer(many=True)},
    )
    @action(detail=False, methods=["get"])
    def mine(self, request: Request) -> Response:
        page = self.paginate_queryset(self.get_queryset().filter(invitee=request.user))
        return self.get_paginated_response(
            InvitationSerializer(page, many=True, context=self.get_serializer_context()).data
        )

    @extend_schema(
        tags=TEAM_TAG,
        summary="Accepter une invitation",
        description="Réservé à la personne invitée ; crée le membre dans la même transaction.",
        request=None,
        responses={200: InvitationSerializer, **errors(401, 403, 404, 409)},
    )
    @action(detail=True, methods=["post"])
    def accept(self, request: Request, pk: str | None = None) -> Response:
        invitation = self.get_object()
        services.accept_invitation(invitation=invitation, actor=request.user)
        return self._respond(invitation)

    @extend_schema(
        tags=TEAM_TAG,
        summary="Décliner une invitation",
        request=None,
        responses={200: InvitationSerializer, **errors(401, 403, 404, 409)},
    )
    @action(detail=True, methods=["post"])
    def decline(self, request: Request, pk: str | None = None) -> Response:
        invitation = self.get_object()
        services.decline_invitation(invitation=invitation, actor=request.user)
        return self._respond(invitation)

    @extend_schema(
        tags=TEAM_TAG,
        summary="Annuler une invitation",
        request=None,
        responses={200: InvitationSerializer, **errors(401, 403, 404, 409)},
    )
    @action(detail=True, methods=["post"])
    def cancel(self, request: Request, pk: str | None = None) -> Response:
        invitation = self.get_object()
        services.cancel_invitation(invitation=invitation, actor=request.user)
        return self._respond(invitation)
