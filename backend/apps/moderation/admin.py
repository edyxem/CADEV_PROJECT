"""Administration : traitement des signalements et consultation des journaux."""

from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest
from rest_framework.exceptions import APIException

from . import services
from .models import AuditLog, ModerationAction, Report


class ReadOnlyAdmin(admin.ModelAdmin):
    """Journaux en ajout seul : ni création, ni modification, ni suppression."""

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return False


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ["__str__", "reporter", "reason", "status", "assigned_to", "created_at"]
    list_filter = ["status", "reason", "target_type"]
    search_fields = ["reporter__username", "details", "target_id"]
    list_select_related = ["reporter", "assigned_to"]
    readonly_fields = [
        "reporter",
        "target_type",
        "target_id",
        "reason",
        "details",
        "status",
        "assigned_to",
        "resolved_at",
        "resolution_note",
        "created_at",
        "updated_at",
    ]
    actions = ["reject_reports", "hide_reported_content"]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def _run(self, request: HttpRequest, queryset: QuerySet, action: str, reason: str) -> None:
        done = 0
        for report in queryset.filter(status__in=Report.OPEN_STATUSES):
            try:
                services.take_action(
                    moderator=request.user, report=report, action=action, reason=reason
                )
                done += 1
            except APIException as exc:
                self.message_user(request, f"{report} : {exc.detail}", messages.WARNING)
        self.message_user(request, f"{done} signalement(s) traité(s) et journalisé(s).")

    @admin.action(description="Rejeter (aucune action)")
    def reject_reports(self, request: HttpRequest, queryset: QuerySet) -> None:
        self._run(
            request, queryset, services.Action.NO_ACTION, "Signalement non fondé (administration)."
        )

    @admin.action(description="Masquer le contenu signalé")
    def hide_reported_content(self, request: HttpRequest, queryset: QuerySet) -> None:
        self._run(
            request, queryset, services.Action.HIDE, "Contenu masqué depuis l'administration."
        )


@admin.register(ModerationAction)
class ModerationActionAdmin(ReadOnlyAdmin):
    list_display = ["action_type", "moderator", "target_type", "target_id", "created_at"]
    list_filter = ["action_type", "target_type"]
    search_fields = ["moderator__username", "target_id", "reason"]
    list_select_related = ["moderator"]


@admin.register(AuditLog)
class AuditLogAdmin(ReadOnlyAdmin):
    list_display = ["action", "actor", "target_type", "target_id", "created_at"]
    list_filter = ["action"]
    search_fields = ["actor__username", "action", "target_id"]
    list_select_related = ["actor"]
