from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("projects", views.ProjectViewSet, basename="project")
router.register("join-requests", views.JoinRequestViewSet, basename="join-request")
router.register("tasks", views.TaskViewSet, basename="task")

urlpatterns = router.urls
