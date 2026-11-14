from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.db.models import QuerySet
from django.http import HttpRequest

from .models import User
from .tokens import revoke_all_sessions


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ["username", "email", "role", "is_active", "email_verified", "date_joined"]
    list_filter = ["role", "is_active", "email_verified"]
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering = ["-date_joined"]
    readonly_fields = ["last_login", "date_joined"]
    actions = ["deactivate_accounts", "reactivate_accounts"]
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Identité", {"fields": ("first_name", "last_name", "email", "email_verified")}),
        ("Accès", {"fields": ("role", "is_active")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "role", "password1", "password2"),
            },
        ),
    )

    def save_model(self, request: HttpRequest, obj: User, form, change: bool) -> None:
        previous = (
            User.objects.filter(pk=obj.pk).values("role", "is_active").first() if change else None
        )
        super().save_model(request, obj, form, change)
        if previous and (previous["role"], previous["is_active"]) != (obj.role, obj.is_active):
            from apps.moderation.services import audit

            audit(
                request.user,
                "account.admin_update",
                target_type="user",
                target_id=obj.pk,
                previous_role=previous["role"],
                new_role=obj.role,
                previous_active=previous["is_active"],
                new_active=obj.is_active,
            )

    @admin.action(description="Désactiver les comptes sélectionnés")
    def deactivate_accounts(self, request: HttpRequest, queryset: QuerySet[User]) -> None:
        targets = queryset.exclude(pk=request.user.pk)
        for user in targets:
            revoke_all_sessions(user)
        updated = targets.update(is_active=False)
        self._audit_bulk(request, targets, "account.admin_deactivate")
        self.message_user(request, f"{updated} compte(s) désactivé(s).", messages.SUCCESS)

    @admin.action(description="Réactiver les comptes sélectionnés")
    def reactivate_accounts(self, request: HttpRequest, queryset: QuerySet[User]) -> None:
        updated = queryset.update(is_active=True)
        self._audit_bulk(request, queryset, "account.admin_reactivate")
        self.message_user(request, f"{updated} compte(s) réactivé(s).", messages.SUCCESS)

    def _audit_bulk(self, request: HttpRequest, queryset: QuerySet[User], action: str) -> None:
        from apps.moderation.services import audit

        for user in queryset:
            audit(request.user, action, target_type="user", target_id=user.pk)
