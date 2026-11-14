from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("mentors", views.MentorViewSet, basename="mentor")
router.register(
    "mentorship-requests", views.MentorshipRequestViewSet, basename="mentorship-request"
)
router.register("mentorship-sessions", views.SessionViewSet, basename="mentorship-session")

urlpatterns = [
    path("mentors/me/", views.MyMentorProfileView.as_view(), name="my-mentor-profile"),
    *router.urls,
]
