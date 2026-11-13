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

    @admin.action(description="Désactiver les comptes sélectionnés")
    def deactivate_accounts(self, request: HttpRequest, queryset: QuerySet[User]) -> None:
        targets = queryset.exclude(pk=request.user.pk)
        for user in targets:
            revoke_all_sessions(user)
        updated = targets.update(is_active=False)
        self.message_user(request, f"{updated} compte(s) désactivé(s).", messages.SUCCESS)

    @admin.action(description="Réactiver les comptes sélectionnés")
    def reactivate_accounts(self, request: HttpRequest, queryset: QuerySet[User]) -> None:
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} compte(s) réactivé(s).", messages.SUCCESS)
