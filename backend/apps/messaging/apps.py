from django.apps import AppConfig


class MessagingConfig(AppConfig):
    name = "apps.messaging"
    label = "messaging"
    verbose_name = "Messagerie privée"

    def ready(self) -> None:
        from apps.moderation import targets
        from apps.moderation.models import TargetType

        from .models import Message

        targets.register(
            TargetType.MESSAGE,
            targets.TargetSpec(
                loader=lambda pk: Message.objects.filter(pk=pk).select_related("sender").first(),
                author=lambda message: message.sender,
                # Seul le message signalé est montré à la modération, jamais la conversation.
                preview=lambda message: {
                    "title": f"Message privé de {message.sender.username}",
                    "excerpt": message.content[:200],
                    "status": "HIDDEN" if message.is_hidden else "VISIBLE",
                    "url": "",
                },
                visible_to=lambda message, user: message.conversation.participants.filter(
                    user=user
                ).exists(),
                actions={targets.Action.WARNING, targets.Action.HIDE, *targets.ACCOUNT_ACTIONS},
                hide=targets.flag_hider("is_hidden"),
            ),
        )
