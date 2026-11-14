"""Recalcule entièrement réputations et badges à partir des données sources."""

from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.reputation.services import sync_user


class Command(BaseCommand):
    help = "Recalcule les événements de contribution, scores et badges de tous les membres."

    def handle(self, *args, **options) -> None:
        total = 0
        for user in User.objects.iterator():
            sync_user(user)
            total += 1
        self.stdout.write(self.style.SUCCESS(f"Réputation recalculée pour {total} membre(s)."))
