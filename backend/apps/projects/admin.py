from django.contrib import admin

from .models import JoinRequest, Project, ProjectMember, ProjectRoleNeed, ProjectTask


class MemberInline(admin.TabularInline):
    model = ProjectMember
    extra = 0
    raw_id_fields = ["user"]
    readonly_fields = ["joined_at", "left_at"]


class RoleNeedInline(admin.TabularInline):
    model = ProjectRoleNeed
    extra = 0
    filter_horizontal = ["required_technologies"]


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "status", "visibility", "accepts_join_requests", "created_at"]
    list_filter = ["status", "visibility", "collaboration_mode", "category"]
    search_fields = ["name", "slug", "owner__username"]
    list_select_related = ["owner", "category"]
    raw_id_fields = ["owner"]
    filter_horizontal = ["technologies"]
    readonly_fields = ["slug", "completed_at", "created_at", "updated_at"]
    inlines = [MemberInline, RoleNeedInline]

    def has_delete_permission(self, request, obj=None) -> bool:
        # Un projet s'archive : son historique et les contributions sont conservés.
        return False


@admin.register(JoinRequest)
class JoinRequestAdmin(admin.ModelAdmin):
    list_display = ["user", "project", "status", "created_at", "reviewed_at"]
    list_filter = ["status"]
    search_fields = ["user__username", "project__name"]
    list_select_related = ["user", "project"]
    raw_id_fields = ["user", "project", "requested_role", "reviewed_by"]


@admin.register(ProjectTask)
class ProjectTaskAdmin(admin.ModelAdmin):
    list_display = ["title", "project", "assignee", "status", "priority", "due_date"]
    list_filter = ["status", "priority"]
    search_fields = ["title", "project__name", "assignee__username"]
    list_select_related = ["project", "assignee"]
    raw_id_fields = ["project", "assignee", "created_by"]
