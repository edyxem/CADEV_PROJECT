"""Indicateurs affichés en tête du tableau de bord de l'administration."""

from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

ACTIVITY_DAYS = 14


def _daily_counts(queryset, field: str, since) -> list[int]:
    """Nombre d'objets créés par jour sur la période, jours vides compris."""
    rows = (
        queryset.filter(**{f"{field}__gte": since})
        .annotate(day=TruncDate(field))
        .values("day")
        .annotate(total=Count("pk"))
    )
    by_day = {row["day"]: row["total"] for row in rows}
    start = since.date()
    return [by_day.get(start + timedelta(days=offset), 0) for offset in range(ACTIVITY_DAYS)]


def collect_stats() -> dict:
    from apps.community.models import ContentStatus, Post
    from apps.events.models import Event
    from apps.moderation.models import Report
    from apps.opportunities.models import Opportunity
    from apps.projects.models import Project

    now = timezone.now()
    since = (now - timedelta(days=ACTIVITY_DAYS - 1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    users = get_user_model().objects.filter(is_active=True)
    posts = Post.objects.filter(status=ContentStatus.PUBLISHED)
    return {
        "kpis": [
            {
                "key": "members",
                "label": "Membres actifs",
                "value": users.count(),
                "icon": "fa-users",
            },
            {
                "key": "posts",
                "label": "Publications",
                "value": posts.count(),
                "icon": "fa-comments",
            },
            {
                "key": "projects",
                "label": "Projets",
                "value": Project.objects.exclude(status=Project.Status.ARCHIVED).count(),
                "icon": "fa-diagram-project",
            },
            {
                "key": "reports",
                "label": "Signalements à traiter",
                "value": Report.objects.filter(
                    status__in=[Report.Status.PENDING, Report.Status.REVIEWING]
                ).count(),
                "icon": "fa-shield-halved",
                "alert": True,
            },
            {
                "key": "opportunities",
                "label": "Annonces à valider",
                "value": Opportunity.objects.filter(
                    status=Opportunity.Status.PENDING_REVIEW
                ).count(),
                "icon": "fa-briefcase",
                "alert": True,
            },
            {
                "key": "events",
                "label": "Événements à venir",
                "value": Event.objects.filter(
                    status=Event.Status.PUBLISHED, starts_at__gte=now
                ).count(),
                "icon": "fa-calendar-days",
            },
        ],
        "activity": {
            "days": ACTIVITY_DAYS,
            "members": _daily_counts(users, "date_joined", since),
            "posts": _daily_counts(posts, "published_at", since),
        },
    }


@never_cache
@require_GET
@staff_member_required
def admin_stats(request: HttpRequest) -> JsonResponse:
    return JsonResponse(collect_stats())
