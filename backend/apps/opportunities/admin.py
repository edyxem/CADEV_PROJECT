from django.contrib import admin, messages
from rest_framework.exceptions import APIException

from .models import Opportunity, OpportunityInterest, Organization
from .services import review_opportunity, verify_organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ["name", "website", "is_verified", "verified_at"]
    list_filter = ["is_verified"]
    search_fields = ["name", "website"]
    filter_horizontal = ["members"]
    readonly_fields = ["slug", "verified_at", "verified_by"]
    actions = ["verify"]

    @admin.action(description="Vérifier les organisations sélectionnées (journalisé)")
    def verify(self, request, queryset) -> None:
        for organization in queryset:
            verify_organization(organization=organization, actor=request.user, verified=True)
        self.message_user(request, f"{queryset.count()} organisation(s) vérifiée(s).")


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "type",
        "organization_label",
        "status",
        "deadline",
        "hidden_by_moderation",
    ]
    list_filter = ["status", "type", "work_mode", "hidden_by_moderation"]
    search_fields = ["title", "organization_name", "organization__name"]
    raw_id_fields = ["publisher", "organization", "reviewed_by"]
    filter_horizontal = ["technologies"]
    actions = ["approve", "reject"]

    def _review(self, request, queryset, *, approve: bool) -> None:
        # Même service que l'API : transitions contrôlées, journal d'audit, auteur notifié.
        done = 0
        for opportunity in queryset:
            try:
                review_opportunity(
                    opportunity=opportunity,
                    moderator=request.user,
                    approve=approve,
                    note="Décision prise depuis l'administration.",
                )
                done += 1
            except APIException as error:
                self.message_user(request, f"{opportunity} : {error.detail}", messages.ERROR)
        if done:
            verb = "publiée(s)" if approve else "refusée(s)"
            self.message_user(request, f"{done} annonce(s) {verb}.", messages.SUCCESS)

    @admin.action(description="Publier les annonces sélectionnées (journalisé)")
    def approve(self, request, queryset) -> None:
        self._review(request, queryset, approve=True)

    @admin.action(description="Refuser les annonces sélectionnées (journalisé)")
    def reject(self, request, queryset) -> None:
        self._review(request, queryset, approve=False)


@admin.register(OpportunityInterest)
class OpportunityInterestAdmin(admin.ModelAdmin):
    list_display = ["user", "opportunity", "kind", "created_at"]
    list_filter = ["kind"]
    raw_id_fields = ["user", "opportunity"]
