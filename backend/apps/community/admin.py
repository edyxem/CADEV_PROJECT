"""Administration des contenus : consultation, masquage et restauration journalisés."""

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from .models import Answer, Comment, ContentStatus, Post


class ContentAdmin(admin.ModelAdmin):
    list_filter = ["status", "created_at"]
    list_select_related = ["author"]
    readonly_fields = ["created_at", "updated_at"]
    actions = ["hide_selection", "restore_selection"]

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return self.model.all_objects.all()

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        # Les contenus ne sont jamais effacés physiquement depuis l'admin.
        return False

    def _moderate(self, request: HttpRequest, queryset: QuerySet, target: str) -> None:
        from apps.moderation.services import moderate_from_admin

        done = sum(moderate_from_admin(obj, target=target, actor=request.user) for obj in queryset)
        self.message_user(request, f"{done} contenu(s) mis à jour et journalisé(s).")

    @admin.action(description="Masquer (modération, journalisé)")
    def hide_selection(self, request: HttpRequest, queryset: QuerySet) -> None:
        self._moderate(request, queryset, ContentStatus.HIDDEN)

    @admin.action(description="Restaurer (journalisé)")
    def restore_selection(self, request: HttpRequest, queryset: QuerySet) -> None:
        self._moderate(request, queryset, ContentStatus.PUBLISHED)


@admin.register(Post)
class PostAdmin(ContentAdmin):
    list_display = ["title", "type", "author", "category", "status", "published_at"]
    list_filter = ["status", "type", "category"]
    search_fields = ["title", "author__username"]
    list_select_related = ["author", "category"]
    autocomplete_fields = ["author", "category", "tags", "technologies"]
    readonly_fields = ["published_at", "last_activity_at", "created_at", "updated_at"]


@admin.register(Comment)
class CommentAdmin(ContentAdmin):
    list_display = ["__str__", "author", "status", "created_at"]
    search_fields = ["content", "author__username"]
    raw_id_fields = ["post", "parent", "author"]


@admin.register(Answer)
class AnswerAdmin(ContentAdmin):
    list_display = ["__str__", "author", "is_accepted", "status", "created_at"]
    list_filter = ["status", "is_accepted"]
    search_fields = ["content", "author__username", "question__title"]
    raw_id_fields = ["question", "author"]
