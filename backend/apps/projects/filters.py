"""Filtres de la liste des projets."""

import django_filters
from django.db.models import Q, QuerySet

from .models import JOINABLE_STATUSES, Project


class ProjectFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=Project.Status.choices)
    category = django_filters.CharFilter(field_name="category__slug")
    technology = django_filters.CharFilter(method="filter_technology")
    mode = django_filters.ChoiceFilter(
        field_name="collaboration_mode", choices=Project.CollaborationMode.choices
    )
    recruiting = django_filters.BooleanFilter(
        method="filter_recruiting", label="Accepte des membres"
    )
    role = django_filters.CharFilter(method="filter_role", label="Rôle recherché (texte)")
    member = django_filters.CharFilter(
        method="filter_member", label="Nom d'utilisateur d'un membre actif du projet"
    )
    q = django_filters.CharFilter(method="filter_q")

    class Meta:
        model = Project
        fields: list[str] = []

    def filter_technology(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        return queryset.filter(technologies__slug=value.lower()).distinct()

    def filter_recruiting(self, queryset: QuerySet, name: str, value: bool | None) -> QuerySet:
        open_projects = Q(accepts_join_requests=True, status__in=JOINABLE_STATUSES)
        if value is None:
            return queryset
        return queryset.filter(open_projects) if value else queryset.exclude(open_projects)

    def filter_member(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        return queryset.filter(
            memberships__user__username__iexact=value.strip(),
            memberships__status="ACTIVE",
        ).distinct()

    def filter_role(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        return queryset.filter(
            role_needs__is_open=True, role_needs__role_name__icontains=value.strip()
        ).distinct()

    def filter_q(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        value = value.strip()
        if not value:
            return queryset
        return queryset.filter(
            Q(name__unaccent__icontains=value)
            | Q(short_description__unaccent__icontains=value)
            | Q(description__unaccent__icontains=value)
        )
