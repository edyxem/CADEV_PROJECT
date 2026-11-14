from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest

from common.exceptions import BusinessRuleViolation

from .models import Category, Country, Tag, Technology
from .services import merge_reference_items


class ReferenceAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "slug"]
    readonly_fields = ["slug", "created_at", "updated_at"]
    actions = ["activate", "deactivate"]

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        # Désactivation logique uniquement : l'historique des contenus est préservé.
        return False

    @admin.action(description="Activer la sélection")
    def activate(self, request: HttpRequest, queryset: QuerySet) -> None:
        self.message_user(request, f"{queryset.update(is_active=True)} élément(s) activé(s).")

    @admin.action(description="Désactiver la sélection")
    def deactivate(self, request: HttpRequest, queryset: QuerySet) -> None:
        self.message_user(request, f"{queryset.update(is_active=False)} élément(s) désactivé(s).")


class MergeableAdmin(ReferenceAdmin):
    actions = [*ReferenceAdmin.actions, "merge_into_first"]

    @admin.action(description="Fusionner dans le premier élément (ordre alphabétique)")
    def merge_into_first(self, request: HttpRequest, queryset: QuerySet) -> None:
        items = list(queryset.order_by("name"))
        if len(items) < 2:
            self.message_user(request, "Sélectionnez au moins deux éléments.", messages.WARNING)
            return
        target, *sources = items
        try:
            for source in sources:
                merge_reference_items(source, target)
        except BusinessRuleViolation as exc:
            self.message_user(request, str(exc.detail), messages.ERROR)
            return
        self.message_user(request, f"{len(sources)} élément(s) fusionné(s) dans « {target} ».")


@admin.register(Category)
class CategoryAdmin(ReferenceAdmin):
    list_display = ["name", "slug", "sort_order", "is_active"]
    list_editable = ["sort_order"]


@admin.register(Tag)
class TagAdmin(MergeableAdmin):
    pass


@admin.register(Technology)
class TechnologyAdmin(MergeableAdmin):
    list_display = ["name", "slug", "category", "is_active"]
    list_filter = ["is_active", "category"]
    list_select_related = ["category"]


@admin.register(Country)
class CountryAdmin(ReferenceAdmin):
    list_display = ["name", "code", "is_active"]
    search_fields = ["name", "code"]
    readonly_fields = ["created_at", "updated_at"]
