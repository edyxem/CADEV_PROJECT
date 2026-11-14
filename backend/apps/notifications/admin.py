from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["recipient", "type", "title", "is_read", "created_at"]
    list_filter = ["type", "is_read"]
    search_fields = ["recipient__username", "title"]
    list_select_related = ["recipient"]
    readonly_fields = [field.name for field in Notification._meta.fields]

    def has_add_permission(self, request) -> bool:
        return False
