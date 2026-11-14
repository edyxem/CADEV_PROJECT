from django.contrib import admin

from .models import DeveloperProfile, SocialLink, UserSkill


class UserSkillInline(admin.TabularInline):
    model = UserSkill
    fk_name = "user"
    extra = 0
    autocomplete_fields = ["technology"]


@admin.register(DeveloperProfile)
class DeveloperProfileAdmin(admin.ModelAdmin):
    list_display = [
        "display_name",
        "user",
        "country",
        "experience_level",
        "availability_status",
        "profile_visibility",
    ]
    list_filter = ["profile_visibility", "availability_status", "experience_level", "country"]
    search_fields = ["display_name", "user__username", "user__email", "city"]
    list_select_related = ["user", "country"]
    autocomplete_fields = ["user", "country"]
    filter_horizontal = ["domains"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(UserSkill)
class UserSkillAdmin(admin.ModelAdmin):
    list_display = ["user", "technology", "level", "verification_status"]
    list_filter = ["verification_status", "level"]
    search_fields = ["user__username", "technology__name"]
    list_select_related = ["user", "technology"]
    autocomplete_fields = ["user", "technology"]
    actions = ["mark_peer_reviewed"]

    @admin.action(description="Marquer comme validée par des pairs")
    def mark_peer_reviewed(self, request, queryset) -> None:
        updated = queryset.update(verification_status=UserSkill.VerificationStatus.PEER_REVIEWED)
        self.message_user(request, f"{updated} compétence(s) validée(s).")


@admin.register(SocialLink)
class SocialLinkAdmin(admin.ModelAdmin):
    list_display = ["user", "platform", "url", "is_public"]
    list_filter = ["platform", "is_public"]
    search_fields = ["user__username", "url"]
    list_select_related = ["user"]
