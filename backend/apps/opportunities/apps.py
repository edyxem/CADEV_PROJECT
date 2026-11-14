from django.apps import AppConfig


class OpportunitiesConfig(AppConfig):
    name = "apps.opportunities"
    label = "opportunities"
    verbose_name = "Opportunités"

    def ready(self) -> None:
        from apps.moderation import targets
        from apps.moderation.models import TargetType

        from .models import Opportunity

        targets.register(
            TargetType.OPPORTUNITY,
            targets.TargetSpec(
                loader=lambda pk: Opportunity.objects.filter(pk=pk).first(),
                author=lambda opportunity: opportunity.publisher,
                preview=lambda opportunity: {
                    "title": opportunity.title,
                    "excerpt": opportunity.organization_label,
                    "status": "HIDDEN" if opportunity.hidden_by_moderation else opportunity.status,
                    "url": f"/opportunites/{opportunity.pk}",
                },
                visible_to=lambda opportunity, user: opportunity.is_publicly_visible,
                actions={
                    targets.Action.WARNING,
                    targets.Action.HIDE,
                    targets.Action.RESTORE,
                    *targets.ACCOUNT_ACTIONS,
                },
                hide=targets.flag_hider(),
            ),
        )
