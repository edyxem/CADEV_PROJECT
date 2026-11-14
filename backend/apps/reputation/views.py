"""Réputation, badges, recommandations et tableau de bord du membre."""

from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.community.models import Answer, Bookmark, ContentStatus, Post
from apps.notifications.models import Notification
from apps.projects.models import JoinRequest, ProjectMember, ProjectTask
from apps.social.models import Follow
from common.permissions import is_moderator
from common.schema import errors

from . import services
from .models import Achievement, Recommendation, UserAchievement
from .serializers import (
    AchievementSerializer,
    DashboardSerializer,
    RecommendationCreateSerializer,
    RecommendationSerializer,
    ReputationSerializer,
)

TAG = ["Réputation"]
EXPLANATION = (
    "Score calculé uniquement à partir de contributions vérifiables (réponses acceptées, votes "
    "utiles reçus, tutoriels, tâches et projets terminés, recommandations), avec plafonds "
    "anti-abus. Aucun point à l'inscription. Le score n'est pas une preuve de compétence."
)


def _visible_member(request: Request, username: str, *, reputation: bool = False) -> User:
    """Membre actif dont le profil est public, ou consulté par lui-même ou la modération."""
    user = get_object_or_404(
        User.objects.select_related("profile"), username__iexact=username, is_active=True
    )
    profile = getattr(user, "profile", None)
    if (
        profile
        and not profile.is_public
        and request.user.pk != user.pk
        and not is_moderator(request.user)
    ):
        raise Http404
    # §I.3 : le membre peut masquer sa réputation, ses badges et recommandations.
    hidden = reputation and profile is not None and not profile.show_reputation
    if hidden and request.user.pk != user.pk and not is_moderator(request.user):
        raise Http404
    return user


class ReputationView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=TAG,
        summary="Réputation et badges d'un membre",
        description="Accès public pour un profil public. Détail des points par type de "
        "contribution ; voir `docs/reputation.md`.",
        responses={200: ReputationSerializer, **errors(404)},
    )
    def get(self, request: Request, username: str) -> Response:
        user = _visible_member(request, username, reputation=True)
        achievements = UserAchievement.objects.filter(user=user).select_related("achievement")
        return Response(
            ReputationSerializer(
                {
                    "username": user.username,
                    "score": services.score_of(user),
                    "breakdown": services.breakdown(user),
                    "achievements": achievements,
                    "explanation": EXPLANATION,
                }
            ).data
        )


@extend_schema(tags=TAG, summary="Badges disponibles et seuils", description="Accès public.")
class AchievementListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = AchievementSerializer
    pagination_class = None
    queryset = Achievement.objects.filter(is_active=True)


class RecommendationListCreateView(generics.GenericAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = RecommendationSerializer
    queryset = Recommendation.objects.none()
    throttle_scope = "content_create"

    @extend_schema(
        tags=TAG,
        summary="Recommandations reçues par un membre",
        responses={200: RecommendationSerializer(many=True), **errors(404)},
    )
    def get(self, request: Request, username: str) -> Response:
        user = _visible_member(request, username, reputation=True)
        queryset = Recommendation.objects.filter(
            recommended=user, recommender__is_active=True
        ).select_related("recommender__profile", "technology")
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(
            RecommendationSerializer(page, many=True, context=self.get_serializer_context()).data
        )

    @extend_schema(
        tags=TAG,
        summary="Recommander un membre",
        description="Réservé aux membres. Contexte concret obligatoire ; une seule "
        "recommandation par couple de membres ; impossible de se recommander soi-même.",
        request=RecommendationCreateSerializer,
        responses={201: RecommendationSerializer, **errors(400, 401, 404, 409, 429)},
    )
    def post(self, request: Request, username: str) -> Response:
        recommended = _visible_member(request, username)
        serializer = RecommendationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        recommendation = services.recommend(
            recommender=request.user, recommended=recommended, **serializer.validated_data
        )
        return Response(
            RecommendationSerializer(recommendation, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )


class RecommendationDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=TAG,
        summary="Retirer une recommandation donnée",
        responses={204: None, **errors(401, 404)},
    )
    def delete(self, request: Request, pk: str) -> Response:
        get_object_or_404(Recommendation, pk=pk, recommender=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Compte"],
        summary="Tableau de bord du membre",
        description="Synthèse personnelle : contributions, notifications, projets et tâches.",
        responses={200: DashboardSerializer, **errors(401)},
    )
    def get(self, request: Request) -> Response:
        user = request.user
        published = ContentStatus.PUBLISHED
        managed = ProjectMember.objects.filter(
            user=user, status=ProjectMember.Status.ACTIVE
        ).filter(
            Q(role=ProjectMember.Role.OWNER)
            | Q(role=ProjectMember.Role.MANAGER, can_manage_members=True)
        )
        return Response(
            {
                "reputation": services.score_of(user),
                "achievements": UserAchievement.objects.filter(user=user).count(),
                "posts": Post.all_objects.filter(author=user, status=published).count(),
                "drafts": Post.all_objects.filter(author=user, status=ContentStatus.DRAFT).count(),
                "answers": Answer.all_objects.filter(author=user, status=published).count(),
                "accepted_answers": Answer.all_objects.filter(
                    author=user, status=published, is_accepted=True
                ).count(),
                "bookmarks": Bookmark.objects.filter(user=user, post__status=published).count(),
                "unread_notifications": Notification.objects.filter(
                    recipient=user, is_read=False
                ).count(),
                "projects": ProjectMember.objects.filter(
                    user=user, status=ProjectMember.Status.ACTIVE
                ).count(),
                "open_tasks": ProjectTask.objects.filter(assignee=user)
                .exclude(status=ProjectTask.Status.DONE)
                .count(),
                "join_requests_to_review": JoinRequest.objects.filter(
                    project__in=managed.values("project"), status=JoinRequest.Status.PENDING
                ).count(),
                "pending_join_requests": JoinRequest.objects.filter(
                    user=user, status=JoinRequest.Status.PENDING
                ).count(),
                "followers": Follow.objects.filter(followed_user=user).count(),
                "following": Follow.objects.filter(follower=user).count(),
            }
        )
