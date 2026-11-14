from django.contrib import admin

from .models import Event, EventRegistration


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ["title", "kind", "format", "starts_at", "status", "hidden_by_moderation"]
    list_filter = ["kind", "format", "status", "hidden_by_moderation"]
    search_fields = ["title", "location"]
    raw_id_fields = ["organizer", "community"]
    filter_horizontal = ["technologies"]


@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ["user", "event", "status", "reminder_sent_at"]
    list_filter = ["status"]
    raw_id_fields = ["user", "event"]
