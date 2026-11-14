"""Configuration de recherche française insensible aux accents."""

from django.contrib.postgres.operations import TrigramExtension, UnaccentExtension
from django.db import migrations

CREATE_CONFIG = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_ts_config WHERE cfgname = 'fr_unaccent') THEN
        CREATE TEXT SEARCH CONFIGURATION fr_unaccent (COPY = french);
        ALTER TEXT SEARCH CONFIGURATION fr_unaccent
            ALTER MAPPING FOR hword, hword_part, word WITH unaccent, french_stem;
    END IF;
END
$$;
"""

DROP_CONFIG = "DROP TEXT SEARCH CONFIGURATION IF EXISTS fr_unaccent;"


class Migration(migrations.Migration):
    initial = True

    dependencies = [("community", "0001_initial")]

    operations = [
        UnaccentExtension(),
        TrigramExtension(),
        migrations.RunSQL(CREATE_CONFIG, DROP_CONFIG),
    ]
