from django.contrib import admin

from .models import Achievement, ContributionEvent, Recommendation, UserAchievement


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "event_type", "threshold", "is_active"]
    list_filter = ["event_type", "is_active"]
    search_fields = ["name", "code"]


@admin.register(ContributionEvent)
class ContributionEventAdmin(admin.ModelAdmin):
    """Lecture seule : les événements sont dérivés des données, jamais saisis."""

    list_display = ["user", "event_type", "points", "created_at"]
    list_filter = ["event_type"]
    search_fields = ["user__username"]
    list_select_related = ["user"]

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False


@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ["user", "achievement", "awarded_at"]
    list_filter = ["achievement"]
    search_fields = ["user__username"]
    list_select_related = ["user", "achievement"]


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ["recommender", "recommended", "technology", "created_at"]
    search_fields = ["recommender__username", "recommended__username", "context"]
    list_select_related = ["recommender", "recommended", "technology"]
    raw_id_fields = ["recommender", "recommended"]
