from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

me_router = SimpleRouter()
me_router.register("profiles/me/links", views.MySocialLinkViewSet, basename="my-link")
me_router.register("profiles/me/portfolio", views.MyPortfolioViewSet, basename="my-portfolio")

router = SimpleRouter()
router.register("profiles", views.ProfileViewSet, basename="profile")

# Les routes « me » sont déclarées avant ``profiles/{username}/`` ; « me » est un nom réservé.
urlpatterns = [
    path("profiles/me/", views.MyProfileView.as_view(), name="my-profile"),
    path("profiles/me/skills/", views.MySkillsView.as_view(), name="my-skills"),
    path("profiles/me/avatar/", views.MyAvatarView.as_view(), name="my-avatar"),
    *me_router.urls,
    path(
        "profiles/<str:username>/portfolio/",
        views.PortfolioView.as_view(),
        name="profile-portfolio",
    ),
    *router.urls,
]
