from django.apps import AppConfig


class MentorshipConfig(AppConfig):
    name = "apps.mentorship"
    label = "mentorship"
    verbose_name = "Mentorat"

    def ready(self) -> None:
        from django.db import transaction
        from django.db.models.signals import post_save

        from .models import MentorshipRequest

        def sync_mentor(sender, instance: MentorshipRequest, **kwargs) -> None:
            from apps.reputation.services import sync_user

            mentor = instance.mentor.user
            transaction.on_commit(lambda: sync_user(mentor))

        post_save.connect(
            sync_mentor, sender=MentorshipRequest, weak=False, dispatch_uid="mentorship.reputation"
        )
