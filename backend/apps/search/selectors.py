"""Recherche dans les contenus et profils publics.

Le point de départ est toujours un sélecteur public (``community.selectors.feed``,
``profiles.selectors.public_profiles``) : un contenu masqué, supprimé ou un
profil privé ne peut donc jamais remonter dans les résultats.
"""

from typing import Any

from django.contrib.postgres.search import (
    SearchQuery,
    SearchRank,
    TrigramSimilarity,
    TrigramWordSimilarity,
)
from django.db.models import F, FloatField, Q, QuerySet, Value
from django.db.models.functions import Coalesce, Greatest

from apps.community import selectors as community_selectors
from apps.community.models import Post
from apps.profiles import selectors as profile_selectors
from apps.profiles.models import DeveloperProfile
from apps.projects import selectors as project_selectors
from apps.projects.models import Project
from common.search import SEARCH_CONFIG

MIN_QUERY_LENGTH = 2
TRIGRAM_THRESHOLD = 0.2
WORD_SIMILARITY_THRESHOLD = 0.5


def normalize_query(raw: str | None) -> str:
    return " ".join((raw or "").split())[:200]


def search_posts(raw_query: str, user: Any) -> QuerySet[Post]:
    """Plein texte pondéré (titre > contenu > environnement) + similarité du titre.

    Le classement combine pertinence puis fraîcheur ; il reste explicable et ne
    dépend pas de la popularité.
    """
    queryset = community_selectors.feed(user)
    query = normalize_query(raw_query)
    if len(query) < MIN_QUERY_LENGTH:
        return queryset.order_by("-published_at")

    search_query = SearchQuery(query, search_type="websearch", config=SEARCH_CONFIG)
    return (
        queryset.annotate(
            text_rank=Coalesce(SearchRank(F("search_vector"), search_query), Value(0.0)),
            title_similarity=TrigramWordSimilarity(query, "title"),
        )
        .annotate(
            rank=Greatest(
                F("text_rank"), F("title_similarity") * Value(0.5), output_field=FloatField()
            )
        )
        .filter(Q(search_vector=search_query) | Q(title_similarity__gte=WORD_SIMILARITY_THRESHOLD))
        .order_by("-rank", "-published_at")
    )


def search_profiles(raw_query: str) -> QuerySet[DeveloperProfile]:
    """Profils publics par nom d'utilisateur, nom d'affichage, titre ou biographie."""
    queryset = profile_selectors.public_profiles()
    query = normalize_query(raw_query)
    if len(query) < MIN_QUERY_LENGTH:
        return queryset.order_by("-created_at")
    return (
        queryset.annotate(
            similarity=Greatest(
                TrigramSimilarity("user__username", query),
                TrigramSimilarity("display_name", query),
                output_field=FloatField(),
            )
        )
        .filter(
            Q(similarity__gte=TRIGRAM_THRESHOLD)
            | Q(user__username__icontains=query)
            | Q(display_name__unaccent__icontains=query)
            | Q(headline__unaccent__icontains=query)
            | Q(bio__unaccent__icontains=query)
        )
        .order_by("-similarity", "-created_at")
    )


def search_projects(raw_query: str) -> QuerySet[Project]:
    """Projets publics non archivés par nom (similarité) ou description."""
    queryset = project_selectors.public_projects()
    query = normalize_query(raw_query)
    if len(query) < MIN_QUERY_LENGTH:
        return queryset.order_by("-created_at")
    return (
        queryset.annotate(similarity=TrigramWordSimilarity(query, "name"))
        .filter(
            Q(similarity__gte=WORD_SIMILARITY_THRESHOLD)
            | Q(name__unaccent__icontains=query)
            | Q(short_description__unaccent__icontains=query)
            | Q(description__unaccent__icontains=query)
            | Q(objectives__unaccent__icontains=query)
        )
        .order_by("-similarity", "-created_at")
    )
