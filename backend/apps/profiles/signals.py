"""Création automatique du profil à l'inscription."""

from typing import Any

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import DeveloperProfile


@receiver(post_save, sender=settings.AUTH_USER_MODEL, dispatch_uid="profiles.create_profile")
def create_profile(sender: Any, instance: Any, created: bool, **kwargs: Any) -> None:
    if created:
        DeveloperProfile.objects.get_or_create(
            user=instance, defaults={"display_name": instance.username}
        )
