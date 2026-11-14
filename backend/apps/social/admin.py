from django.contrib import admin

from .models import Follow


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = [
        "follower",
        "target_type",
        "followed_user",
        "technology",
        "category",
        "created_at",
    ]
    list_filter = ["target_type"]
    search_fields = ["follower__username", "followed_user__username"]
    list_select_related = ["follower", "followed_user", "technology", "category"]
    raw_id_fields = ["follower", "followed_user"]
