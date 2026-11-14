"""Requêtes de lecture des profils, optimisées contre le N+1."""

from django.db.models import Prefetch, QuerySet

from .models import DeveloperProfile, SocialLink, UserSkill


def profiles_with_relations() -> QuerySet[DeveloperProfile]:
    return DeveloperProfile.objects.select_related("user", "country").prefetch_related(
        "domains",
        Prefetch(
            "user__skills",
            queryset=UserSkill.objects.select_related("technology"),
        ),
        Prefetch(
            "user__social_links",
            queryset=SocialLink.objects.filter(is_public=True),
            to_attr="public_links",
        ),
    )


def public_profiles() -> QuerySet[DeveloperProfile]:
    """Profils publics de comptes actifs : seule base de l'annuaire et de la recherche."""
    return profiles_with_relations().filter(
        user__is_active=True, profile_visibility=DeveloperProfile.Visibility.PUBLIC
    )
