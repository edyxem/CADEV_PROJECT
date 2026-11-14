"""Routes de l'API v1."""

from django.urls import include, path

from common.views import HealthView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("", include("apps.accounts.urls")),
    path("", include("apps.catalog.urls")),
    path("", include("apps.profiles.urls")),
    path("", include("apps.notifications.urls")),
    path("", include("apps.community.urls")),
    path("", include("apps.projects.urls")),
    path("", include("apps.moderation.urls")),
    path("", include("apps.social.urls")),
    path("", include("apps.reputation.urls")),
    path("", include("apps.opportunities.urls")),
    path("", include("apps.mentorship.urls")),
    path("", include("apps.communities.urls")),
    path("", include("apps.events.urls")),
    path("", include("apps.messaging.urls")),
    path("", include("apps.search.urls")),
]
