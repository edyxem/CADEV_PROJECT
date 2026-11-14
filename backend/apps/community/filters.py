"""Filtres du fil communautaire (§C.2, §F.1)."""

import django_filters
from django.db.models import Q, QuerySet

from .models import Post


class PostFilter(django_filters.FilterSet):
    type = django_filters.ChoiceFilter(choices=Post.Type.choices)
    category = django_filters.CharFilter(field_name="category__slug")
    technology = django_filters.CharFilter(method="filter_technology")
    tag = django_filters.CharFilter(method="filter_tag")
    author = django_filters.CharFilter(
        method="filter_author", label="Nom d'utilisateur (profils publics uniquement)"
    )
    q = django_filters.CharFilter(method="filter_q", label="Mots du titre ou du contenu")
    unanswered = django_filters.BooleanFilter(method="filter_unanswered")

    class Meta:
        model = Post
        fields: list[str] = []

    def filter_author(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        """§F.1 : on ne recherche par auteur que si son profil est public."""
        return queryset.filter(
            author__username__iexact=value.strip(),
            author__profile__profile_visibility="PUBLIC",
        )

    def filter_technology(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        return queryset.filter(technologies__slug=value.lower()).distinct()

    def filter_tag(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        return queryset.filter(tags__slug=value.lower()).distinct()

    def filter_q(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        value = value.strip()
        if not value:
            return queryset
        return queryset.filter(Q(title__icontains=value) | Q(content__icontains=value))

    def filter_unanswered(self, queryset: QuerySet, name: str, value: bool | None) -> QuerySet:
        if value:
            return queryset.filter(type=Post.Type.QUESTION, answer_count=0)
        return queryset
