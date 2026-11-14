from django.apps import AppConfig


class ReputationConfig(AppConfig):
    name = "apps.reputation"
    label = "reputation"
    verbose_name = "Réputation et badges"

    def ready(self) -> None:
        from . import signals  # noqa: F401
