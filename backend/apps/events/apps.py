from django.apps import AppConfig


class EventsConfig(AppConfig):
    name = "apps.events"
    label = "events"
    verbose_name = "Événements"

    def ready(self) -> None:
        from apps.moderation import targets
        from apps.moderation.models import TargetType

        from .models import Event

        targets.register(
            TargetType.EVENT,
            targets.TargetSpec(
                loader=lambda pk: Event.objects.filter(pk=pk).first(),
                author=lambda event: event.organizer,
                preview=lambda event: {
                    "title": event.title,
                    "excerpt": event.location or event.get_format_display(),
                    "status": "HIDDEN" if event.hidden_by_moderation else event.status,
                    "url": f"/evenements/{event.pk}",
                },
                visible_to=lambda event, user: not event.hidden_by_moderation,
                actions={
                    targets.Action.WARNING,
                    targets.Action.HIDE,
                    targets.Action.RESTORE,
                    *targets.ACCOUNT_ACTIONS,
                },
                hide=targets.flag_hider(),
            ),
        )
