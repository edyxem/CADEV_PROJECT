from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("follows", views.FollowViewSet, basename="follow")

urlpatterns = [
    path("feed/", views.PersonalFeedView.as_view(), name="personal-feed"),
    path(
        "profiles/<str:username>/follow-stats/",
        views.FollowStatsView.as_view(),
        name="follow-stats",
    ),
    *router.urls,
]
