"""Stockage des fichiers statiques."""

from whitenoise.storage import CompressedManifestStaticFilesStorage


class StaticStorage(CompressedManifestStaticFilesStorage):
    """Fichiers compressés et hachés (cache long), en mode non strict.

    Le gabarit de base de Jazzmin référence un dossier (``{% static 'vendor/bootswatch' %}``)
    qui n'a pas d'entrée dans le manifeste : en mode strict, toute page de l'administration
    renverrait une erreur 500. Les fichiers réels restent servis sous leur nom haché.
    """

    manifest_strict = False
