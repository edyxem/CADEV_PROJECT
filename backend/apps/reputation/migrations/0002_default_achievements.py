"""Badges par défaut (seuils documentés dans docs/reputation.md)."""

from django.db import migrations


def create_achievements(apps, schema_editor):
    from apps.reputation.rules import DEFAULT_ACHIEVEMENTS

    Achievement = apps.get_model("reputation", "Achievement")
    for code, name, description, icon_key, event_type, threshold in DEFAULT_ACHIEVEMENTS:
        Achievement.objects.get_or_create(
            code=code,
            defaults={
                "name": name,
                "description": description,
                "icon_key": icon_key,
                "event_type": event_type,
                "threshold": threshold,
            },
        )


class Migration(migrations.Migration):
    dependencies = [("reputation", "0001_initial")]

    operations = [migrations.RunPython(create_achievements, migrations.RunPython.noop)]
