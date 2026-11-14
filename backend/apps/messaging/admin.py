"""Administration de la messagerie.

Le contenu des conversations n'est pas consultable dans l'admin : seuls les
messages signalés sont présentés à la modération, via la file des signalements.
"""

from django.contrib import admin

from .models import Block, Conversation


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ["id", "last_message_at", "created_at"]
    readonly_fields = ["participants_key", "last_message_at", "created_at", "updated_at"]

    def has_add_permission(self, request) -> bool:
        return False


@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = ["blocker", "blocked", "created_at"]
    search_fields = ["blocker__username", "blocked__username"]
    raw_id_fields = ["blocker", "blocked"]
