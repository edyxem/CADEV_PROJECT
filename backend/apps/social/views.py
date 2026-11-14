"""Endpoints des abonnements et du fil personnalisé."""

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.community.serializers import PostListSerializer
from common.schema import errors

from . import services
from .models import Follow
from .serializers import (
    FollowCreateSerializer,
    FollowerSerializer,
    FollowSerializer,
    FollowStatsSerializer,
)

TAG = ["Abonnements"]


@extend_schema_view(
    list=extend_schema(
        tags=TAG,
        summary="Mes abonnements",
        parameters=[OpenApiParameter("target_type", str, enum=Follow.TargetType.values)],
    ),
    create=extend_schema(
        tags=TAG,
        summary="Suivre un membre, une technologie ou une catégorie",
        description="Réservé aux membres. Impossible de se suivre soi-même ou de suivre deux fois.",
        request=FollowCreateSerializer,
        responses={201: FollowSerializer, **errors(400, 401, 409)},
    ),
    destroy=extend_schema(
        tags=TAG, summary="Ne plus suivre", responses={204: None, **errors(401, 404)}
    ),
)
class FollowViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    serializer_class = FollowSerializer

    def get_queryset(self) -> QuerySet[Follow]:
        if getattr(self, "swagger_fake_view", False):  # génération du schéma OpenAPI
            return Follow.objects.none()
        queryset = Follow.objects.filter(follower=self.request.user).select_related(
            "followed_user__profile", "technology", "category"
        )
        wanted = self.request.query_params.get("target_type")
        return (
            queryset.filter(target_type=wanted) if wanted in Follow.TargetType.values else queryset
        )

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = FollowCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscription = services.follow(follower=request.user, **serializer.validated_data)
        return Response(
            FollowSerializer(subscription, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        tags=TAG,
        summary="Mes abonnés",
        responses={200: FollowerSerializer(many=True), **errors(401)},
    )
    @action(detail=False, methods=["get"])
    def followers(self, request: Request) -> Response:
        queryset = Follow.objects.filter(
            target_type=Follow.TargetType.USER, followed_user=request.user, follower__is_active=True
        ).select_related("follower__profile")
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(
            FollowerSerializer(page, many=True, context=self.get_serializer_context()).data
        )


@extend_schema(
    tags=TAG,
    summary="Fil personnalisé",
    description="Publications des membres, technologies et catégories suivis. Complète le fil "
    "général `/posts/`, qui reste toujours accessible.",
    responses={200: PostListSerializer(many=True), **errors(401)},
)
class PersonalFeedView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PostListSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # génération du schéma OpenAPI
            from apps.community.models import Post

            return Post.all_objects.none()
        return services.personal_feed(self.request.user)


class FollowStatsView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=TAG,
        summary="Compteurs d'abonnement d'un membre",
        description="Accès public, comptes actifs uniquement.",
        responses={200: FollowStatsSerializer, **errors(404)},
    )
    def get(self, request: Request, username: str) -> Response:
        user = get_object_or_404(User, username__iexact=username, is_active=True)
        return Response(
            {
                "followers": Follow.objects.filter(
                    target_type=Follow.TargetType.USER, followed_user=user, follower__is_active=True
                ).count(),
                "following": Follow.objects.filter(follower=user).count(),
            }
        )
