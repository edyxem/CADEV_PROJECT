"""Filtres de l'annuaire des développeurs (§F.2).

Les champs masqués par leur titulaire ne servent jamais de critère : filtrer
par ville ou disponibilité ignore les profils qui les ont rendus privés.
"""

import django_filters
from django.db.models import Q, QuerySet

from .models import DeveloperProfile, ExperienceLevel, Language


class ProfileFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method="filter_q", label="Recherche libre")
    technology = django_filters.CharFilter(method="filter_technology", label="Slug de technologie")
    domain = django_filters.CharFilter(field_name="domains__slug", label="Slug de domaine")
    country = django_filters.CharFilter(method="filter_country", label="Code pays ISO")
    city = django_filters.CharFilter(method="filter_city", label="Ville")
    availability = django_filters.ChoiceFilter(
        choices=DeveloperProfile.Availability.choices, method="filter_availability"
    )
    level = django_filters.ChoiceFilter(
        field_name="experience_level", choices=ExperienceLevel.choices
    )
    language = django_filters.ChoiceFilter(choices=Language.choices, method="filter_language")
    ordering = django_filters.OrderingFilter(
        fields=(("created_at", "recent"), ("user__username", "username")),
        label="Tri : recent, -recent, username",
    )

    class Meta:
        model = DeveloperProfile
        fields: list[str] = []

    def filter_q(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        value = value.strip()
        if not value:
            return queryset
        return queryset.filter(
            Q(user__username__icontains=value)
            | Q(display_name__icontains=value)
            | Q(headline__icontains=value)
            | Q(bio__icontains=value)
        )

    def filter_technology(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        return queryset.filter(user__skills__technology__slug=value.lower())

    def filter_country(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        return queryset.filter(country__code=value.upper())

    def filter_city(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        return queryset.filter(show_city=True, city__iexact=value.strip())

    def filter_availability(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        return queryset.filter(show_availability=True, availability_status=value)

    def filter_language(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        return queryset.filter(languages__contains=[value])

    @property
    def qs(self) -> QuerySet:
        return super().qs.distinct()
