from django.contrib import admin

from .models import MentorProfile, MentorshipFeedback, MentorshipRequest, MentorshipSession


@admin.register(MentorProfile)
class MentorProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "headline", "is_available", "max_active_mentees"]
    list_filter = ["is_available"]
    search_fields = ["user__username", "headline"]
    raw_id_fields = ["user"]
    filter_horizontal = ["domains", "technologies"]


@admin.register(MentorshipRequest)
class MentorshipRequestAdmin(admin.ModelAdmin):
    list_display = ["mentee", "mentor", "status", "created_at"]
    list_filter = ["status"]
    raw_id_fields = ["mentee", "mentor"]


@admin.register(MentorshipSession)
class MentorshipSessionAdmin(admin.ModelAdmin):
    list_display = ["request", "scheduled_at", "status"]
    list_filter = ["status"]
    raw_id_fields = ["request"]


@admin.register(MentorshipFeedback)
class MentorshipFeedbackAdmin(admin.ModelAdmin):
    list_display = ["session", "author", "rating", "created_at"]
    raw_id_fields = ["session", "author"]
