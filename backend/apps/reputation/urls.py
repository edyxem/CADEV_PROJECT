from django.urls import path

from . import views

urlpatterns = [
    path("achievements/", views.AchievementListView.as_view(), name="achievements"),
    path("me/dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path(
        "profiles/<str:username>/reputation/",
        views.ReputationView.as_view(),
        name="profile-reputation",
    ),
    path(
        "profiles/<str:username>/recommendations/",
        views.RecommendationListCreateView.as_view(),
        name="profile-recommendations",
    ),
    path(
        "recommendations/<uuid:pk>/",
        views.RecommendationDeleteView.as_view(),
        name="recommendation-delete",
    ),
]
