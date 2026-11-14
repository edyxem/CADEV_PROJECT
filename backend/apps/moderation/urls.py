from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("reports", views.ReportViewSet, basename="report")
router.register("moderation/reports", views.ModerationReportViewSet, basename="moderation-report")
router.register("moderation/actions", views.ModerationActionViewSet, basename="moderation-action")
router.register("moderation/audit-logs", views.AuditLogViewSet, basename="audit-log")

urlpatterns = [
    path("moderation/stats/", views.ModerationStatsView.as_view(), name="moderation-stats"),
    *router.urls,
]
