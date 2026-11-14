from django.apps import AppConfig


class ProfilesConfig(AppConfig):
    name = "apps.profiles"
    label = "profiles"
    verbose_name = "Profils développeurs"

    def ready(self) -> None:
        from . import signals  # noqa: F401
