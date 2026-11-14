"""Endpoints de recherche, publics et limités en débit."""

from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import generics, serializers
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.community.filters import PostFilter
from apps.community.serializers import PostListSerializer
from apps.profiles.filters import ProfileFilter
from apps.profiles.serializers import PublicProfileSerializer
from apps.projects.filters import ProjectFilter
from apps.projects.serializers import ProjectListSerializer
from common.schema import errors

from . import selectors

TAG = ["Recherche"]
Q_PARAM = OpenApiParameter(
    "q",
    str,
    description="Mots recherchés (2 caractères minimum ; guillemets et `-mot` acceptés). "
    "Insensible à la casse et aux accents.",
)
PREVIEW_SIZE = 5


class SearchThrottleMixin:
    permission_classes = [AllowAny]
    throttle_scope = "search"
    throttle_safe_methods = True


class RankedSearchMixin(SearchThrottleMixin):
    """Applique les filtres de liste sauf ``q``, déjà traité par la recherche classée."""

    def filter_queryset(self, queryset):
        params = self.request.query_params.copy()
        params.pop("q", None)
        return self.filterset_class(params, queryset=queryset, request=self.request).qs


@extend_schema(
    tags=TAG,
    summary="Rechercher des publications",
    description="Accès public. Publications publiées uniquement, classées par pertinence puis "
    "date. Accepte aussi les filtres du fil (`type`, `category`, `technology`, `tag`, `author`).",
    parameters=[Q_PARAM],
    responses={200: PostListSerializer(many=True), **errors(429)},
)
class PostSearchView(RankedSearchMixin, generics.ListAPIView):
    serializer_class = PostListSerializer
    filterset_class = PostFilter

    def get_queryset(self):
        return selectors.search_posts(self.request.query_params.get("q", ""), self.request.user)


@extend_schema(
    tags=TAG,
    summary="Rechercher des développeurs",
    description="Accès public. Profils publics uniquement ; mêmes filtres que l'annuaire "
    "(`technology`, `country`, `domain`, `availability`, `level`, `language`, `city`).",
    parameters=[Q_PARAM],
    responses={200: PublicProfileSerializer(many=True), **errors(429)},
)
class UserSearchView(RankedSearchMixin, generics.ListAPIView):
    serializer_class = PublicProfileSerializer
    filterset_class = ProfileFilter

    def get_queryset(self):
        return selectors.search_profiles(self.request.query_params.get("q", ""))


@extend_schema(
    tags=TAG,
    summary="Rechercher des projets",
    description="Accès public. Projets publics non archivés ; mêmes filtres que la liste des "
    "projets (`status`, `technology`, `category`, `recruiting`, `role`, `mode`).",
    parameters=[Q_PARAM],
    responses={200: ProjectListSerializer(many=True), **errors(429)},
)
class ProjectSearchView(RankedSearchMixin, generics.ListAPIView):
    serializer_class = ProjectListSerializer
    filterset_class = ProjectFilter

    def get_queryset(self):
        return selectors.search_projects(self.request.query_params.get("q", ""))


class GlobalSearchView(SearchThrottleMixin, APIView):
    """Aperçu combiné : quelques résultats par type de ressource."""

    @extend_schema(
        tags=TAG,
        summary="Recherche générale",
        description="Accès public. Renvoie les 5 meilleurs résultats de chaque type ; utiliser "
        "les endpoints dédiés pour la pagination.",
        parameters=[Q_PARAM],
        responses={
            200: inline_serializer(
                "GlobalSearchResponse",
                {
                    "query": serializers.CharField(),
                    "posts": PostListSerializer(many=True),
                    "users": PublicProfileSerializer(many=True),
                    "projects": ProjectListSerializer(many=True),
                },
            ),
            **errors(429),
        },
    )
    def get(self, request: Request) -> Response:
        query = selectors.normalize_query(request.query_params.get("q"))
        context = {"request": request}
        if len(query) < selectors.MIN_QUERY_LENGTH:
            return Response({"query": query, "posts": [], "users": [], **self.extra_empty()})
        posts = selectors.search_posts(query, request.user)[:PREVIEW_SIZE]
        users = selectors.search_profiles(query)[:PREVIEW_SIZE]
        return Response(
            {
                "query": query,
                "posts": PostListSerializer(posts, many=True, context=context).data,
                "users": PublicProfileSerializer(users, many=True, context=context).data,
                **self.extra_results(query, request),
            }
        )

    def extra_results(self, query: str, request: Request) -> dict:
        projects = selectors.search_projects(query)[:PREVIEW_SIZE]
        context = {"request": request}
        return {"projects": ProjectListSerializer(projects, many=True, context=context).data}

    def extra_empty(self) -> dict:
        return {"projects": []}
