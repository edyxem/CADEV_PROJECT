"""Recalcule les vecteurs de recherche de toutes les publications."""

from django.core.management.base import BaseCommand

from apps.community.models import Post
from apps.community.services import refresh_search_vector


class Command(BaseCommand):
    help = (
        "Reconstruit l'index plein texte des publications (après import ou changement de config)."
    )

    def handle(self, *args, **options) -> None:
        count = 0
        for post in Post.all_objects.only("pk").iterator():
            refresh_search_vector(post)
            count += 1
        self.stdout.write(self.style.SUCCESS(f"{count} publication(s) réindexée(s)."))
