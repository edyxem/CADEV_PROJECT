"""Recommandations explicables de développeurs et de projets (P2).

Le classement repose uniquement sur le recouvrement de technologies (compétences
déclarées et technologies suivies) : aucun score opaque ni popularité.
"""

from django.db.models import Count, Q, QuerySet

from apps.accounts.models import User
from apps.profiles import selectors as profile_selectors
from apps.profiles.models import DeveloperProfile, UserSkill
from apps.projects import selectors as project_selectors
from apps.projects.models import JOINABLE_STATUSES, Project, ProjectMember

from .models import Follow


def interest_technologies(user: User) -> list:
    skills = UserSkill.objects.filter(user=user).values_list("technology_id", flat=True)
    followed = Follow.objects.filter(
        follower=user, target_type=Follow.TargetType.TECHNOLOGY
    ).values_list("technology_id", flat=True)
    return list({*skills, *followed})


def recommended_developers(user: User) -> QuerySet[DeveloperProfile]:
    technologies = interest_technologies(user)
    already_followed = Follow.objects.filter(
        follower=user, target_type=Follow.TargetType.USER
    ).values("followed_user")
    return (
        profile_selectors.public_profiles()
        .exclude(user=user)
        .exclude(user__in=already_followed)
        .annotate(
            shared=Count(
                "user__skills", filter=Q(user__skills__technology__in=technologies), distinct=True
            )
        )
        .filter(shared__gt=0)
        .order_by("-shared", "-created_at")
    )


def recommended_projects(user: User) -> QuerySet[Project]:
    technologies = interest_technologies(user)
    mine = ProjectMember.objects.filter(user=user, status=ProjectMember.Status.ACTIVE).values(
        "project"
    )
    return (
        project_selectors.public_projects()
        .filter(accepts_join_requests=True, status__in=JOINABLE_STATUSES)
        .exclude(pk__in=mine)
        .annotate(
            shared=Count("technologies", filter=Q(technologies__in=technologies), distinct=True)
        )
        .filter(shared__gt=0)
        .order_by("-shared", "-created_at")
    )
