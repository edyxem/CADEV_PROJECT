"""Rappels d'événements (à planifier, par exemple toutes les heures via cron)."""

from django.core.management.base import BaseCommand

from apps.events.services import send_reminders


class Command(BaseCommand):
    help = "Notifie les inscrits des événements qui commencent dans les 24 heures (une seule fois)."

    def handle(self, *args, **options) -> None:
        self.stdout.write(self.style.SUCCESS(f"{send_reminders()} rappel(s) envoyé(s)."))
