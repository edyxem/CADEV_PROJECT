from django.contrib import admin

from .models import Community, CommunityMembership


class MembershipInline(admin.TabularInline):
    model = CommunityMembership
    extra = 0
    raw_id_fields = ["user"]


@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ["name", "kind", "country", "hidden_by_moderation", "created_at"]
    list_filter = ["kind", "hidden_by_moderation"]
    search_fields = ["name", "slug"]
    raw_id_fields = ["created_by"]
    readonly_fields = ["slug"]
    inlines = [MembershipInline]
