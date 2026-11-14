"""Charge les référentiels (catégories, technologies, tags, pays). Idempotent."""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog import reference_data
from apps.catalog.models import Category, Country, Tag, Technology
from apps.catalog.normalization import make_slug


def seed_reference() -> dict[str, int]:
    """Crée les éléments manquants sans modifier ceux qu'un admin a déjà ajustés."""
    created = dict.fromkeys(["categories", "technologies", "tags", "countries"], 0)
    with transaction.atomic():
        for order, (name, description) in enumerate(reference_data.CATEGORIES, start=1):
            _, is_new = Category.objects.get_or_create(
                slug=make_slug(name),
                defaults={"name": name, "description": description, "sort_order": order},
            )
            created["categories"] += is_new

        categories = {category.slug: category for category in Category.objects.all()}
        for name, category_slug in reference_data.TECHNOLOGIES:
            _, is_new = Technology.objects.get_or_create(
                slug=make_slug(name),
                defaults={"name": name, "category": categories.get(category_slug)},
            )
            created["technologies"] += is_new

        for name in reference_data.TAGS:
            _, is_new = Tag.objects.get_or_create(slug=make_slug(name), defaults={"name": name})
            created["tags"] += is_new

        for code, name in reference_data.AFRICAN_COUNTRIES:
            _, is_new = Country.objects.get_or_create(code=code, defaults={"name": name})
            created["countries"] += is_new
    return created


class Command(BaseCommand):
    help = "Charge les référentiels de base (utilisable en production). Idempotent."

    def handle(self, *args, **options) -> None:
        created = seed_reference()
        summary = ", ".join(f"{count} {label}" for label, count in created.items())
        self.stdout.write(self.style.SUCCESS(f"Référentiels à jour ({summary} créés)."))
