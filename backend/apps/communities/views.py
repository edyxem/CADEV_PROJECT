"""Endpoints des communautés."""

from django.db.models import Count, Q, QuerySet
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.request import Request
from rest_framework.response import Response

from apps.community import selectors as community_selectors
from apps.community.models import Post
from apps.community.serializers import PostListSerializer
from common.permissions import is_moderator
from common.schema import errors

from . import services
from .models import Community, CommunityMembership
from .serializers import (
    CommunitySerializer,
    CommunityWriteSerializer,
    LocalModerationSerializer,
    MembershipSerializer,
    MembershipUpdateSerializer,
)

TAG = ["Communautés"]
UUID_RE = "[0-9a-f-]{36}"


@extend_schema_view(
    list=extend_schema(
        tags=TAG,
        summary="Lister les communautés",
        parameters=[
            OpenApiParameter("kind", str, enum=Community.Kind.values),
            OpenApiParameter("country", str),
            OpenApiParameter("technology", str),
            OpenApiParameter("q", str),
        ],
    ),
    retrieve=extend_schema(tags=TAG, summary="Détail d'une communauté"),
    create=extend_schema(
        tags=TAG,
        summary="Créer une communauté",
        description="Le créateur en devient responsable.",
        request=CommunityWriteSerializer,
        responses={201: CommunitySerializer, **errors(400, 401, 429)},
    ),
    partial_update=extend_schema(
        tags=TAG,
        summary="Modifier une communauté",
        description="Réservé aux responsables.",
        request=CommunityWriteSerializer,
        responses={200: CommunitySerializer, **errors(400, 401, 403, 404)},
    ),
)
class CommunityViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = CommunitySerializer
    lookup_field = "slug"
    http_method_names = ["get", "post", "patch", "head", "options"]
    throttle_scope = "content_create"

    def get_queryset(self) -> QuerySet[Community]:
        queryset = Community.objects.select_related("country", "technology", "category").annotate(
            member_count=Count(
                "memberships", filter=Q(memberships__status=CommunityMembership.Status.ACTIVE)
            )
        )
        if not is_moderator(self.request.user):
            queryset = queryset.filter(hidden_by_moderation=False)
        params = self.request.query_params
        if self.action == "list":
            if params.get("kind"):
                queryset = queryset.filter(kind=params["kind"])
            if params.get("country"):
                queryset = queryset.filter(country__code=params["country"].upper())
            if params.get("technology"):
                queryset = queryset.filter(technology__slug=params["technology"])
            if params.get("q"):
                queryset = queryset.filter(
                    Q(name__unaccent__icontains=params["q"])
                    | Q(description__unaccent__icontains=params["q"])
                )
        return queryset.order_by("name")

    def _respond(self, community: Community, status_code: int = status.HTTP_200_OK) -> Response:
        community = self.get_queryset().get(pk=community.pk)
        return Response(
            CommunitySerializer(community, context=self.get_serializer_context()).data,
            status=status_code,
        )

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = CommunityWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        community = services.create_community(creator=request.user, data=serializer.validated_data)
        return self._respond(community, status.HTTP_201_CREATED)

    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        community = self.get_object()
        serializer = CommunityWriteSerializer(community, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        services.update_community(
            community=community, actor=request.user, data=serializer.validated_data
        )
        return self._respond(community)

    @extend_schema(
        tags=TAG,
        summary="Rejoindre",
        request=None,
        responses={201: MembershipSerializer, **errors(401, 404, 409)},
    )
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def join(self, request: Request, slug: str | None = None) -> Response:
        member = services.join(community=self.get_object(), user=request.user)
        return Response(
            MembershipSerializer(member, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        tags=TAG,
        summary="Quitter",
        description="Le dernier responsable doit d'abord en désigner un autre.",
        request=None,
        responses={204: None, **errors(401, 404, 409)},
    )
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def leave(self, request: Request, slug: str | None = None) -> Response:
        services.leave(community=self.get_object(), user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(tags=TAG, summary="Membres", responses={200: MembershipSerializer(many=True)})
    @action(detail=True, methods=["get"])
    def members(self, request: Request, slug: str | None = None) -> Response:
        community = self.get_object()
        queryset = community.memberships.filter(
            status=CommunityMembership.Status.ACTIVE
        ).select_related("user__profile")
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(
            MembershipSerializer(page, many=True, context=self.get_serializer_context()).data
        )

    @extend_schema(
        tags=TAG,
        summary="Gérer un membre",
        description="Responsables : nommer responsable, rétrograder ou exclure "
        "(`ban`, journalisé).",
        request=MembershipUpdateSerializer,
        responses={200: MembershipSerializer, **errors(400, 401, 403, 404, 409)},
    )
    @action(
        detail=True,
        methods=["patch"],
        url_path=f"members/(?P<member_id>{UUID_RE})",
        permission_classes=[IsAuthenticated],
    )
    def member_detail(
        self, request: Request, slug: str | None = None, member_id: str | None = None
    ) -> Response:
        community = self.get_object()
        member = get_object_or_404(
            CommunityMembership,
            pk=member_id,
            community=community,
            status=CommunityMembership.Status.ACTIVE,
        )
        serializer = MembershipUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        member = services.manage_member(
            member=member, actor=request.user, **serializer.validated_data
        )
        return Response(MembershipSerializer(member, context=self.get_serializer_context()).data)

    @extend_schema(
        tags=TAG,
        summary="Fil de la communauté",
        description="Publications publiées dans la communauté, hors retraits locaux.",
        responses={200: PostListSerializer(many=True)},
    )
    @action(detail=True, methods=["get"])
    def posts(self, request: Request, slug: str | None = None) -> Response:
        community = self.get_object()
        queryset = community_selectors.feed(request.user).filter(
            community=community, community_hidden=False
        )
        page = self.paginate_queryset(queryset.order_by("-published_at"))
        return self.get_paginated_response(
            PostListSerializer(page, many=True, context=self.get_serializer_context()).data
        )

    @extend_schema(
        tags=TAG,
        summary="Modération locale d'une publication",
        description="Responsables : retirer (ou rétablir) une publication du fil de la communauté. "
        "Journalisé ; l'auteur est informé. La modération globale reste prioritaire.",
        request=LocalModerationSerializer,
        responses={200: PostListSerializer, **errors(400, 401, 403, 404)},
    )
    @action(
        detail=True,
        methods=["post"],
        url_path=f"posts/(?P<post_id>{UUID_RE})/moderate",
        permission_classes=[IsAuthenticated],
    )
    def moderate_post(
        self, request: Request, slug: str | None = None, post_id: str | None = None
    ) -> Response:
        community = self.get_object()
        post = get_object_or_404(Post.all_objects, pk=post_id)
        serializer = LocalModerationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.set_post_visibility(
            community=community, post=post, actor=request.user, **serializer.validated_data
        )
        post = community_selectors.annotate_posts(
            Post.all_objects.filter(pk=post.pk), request.user
        ).get()
        return Response(PostListSerializer(post, context=self.get_serializer_context()).data)
