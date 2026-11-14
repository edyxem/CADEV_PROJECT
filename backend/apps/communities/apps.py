from django.apps import AppConfig


class CommunitiesConfig(AppConfig):
    name = "apps.communities"
    label = "communities"
    verbose_name = "Communautés thématiques et géographiques"

    def ready(self) -> None:
        from apps.moderation import targets
        from apps.moderation.models import TargetType

        from .models import Community

        targets.register(
            TargetType.COMMUNITY,
            targets.TargetSpec(
                loader=lambda pk: Community.objects.filter(pk=pk).first(),
                author=lambda community: community.created_by,
                preview=lambda community: {
                    "title": community.name,
                    "excerpt": community.description[:200],
                    "status": "HIDDEN" if community.hidden_by_moderation else "VISIBLE",
                    "url": f"/communautes/{community.slug}",
                },
                visible_to=lambda community, user: not community.hidden_by_moderation,
                actions={targets.Action.WARNING, targets.Action.HIDE, targets.Action.RESTORE},
                hide=targets.flag_hider(),
            ),
        )
