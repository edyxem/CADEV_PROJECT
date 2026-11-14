"""Normalisation des images téléversées (avatars, logos)."""

import io
import uuid

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from PIL import Image, ImageOps

from common.validators import validate_image_upload


def normalized_image(upload: UploadedFile, *, max_size: tuple[int, int]) -> ContentFile:
    """Valide puis réencode l'image en WebP : métadonnées supprimées, poids et taille bornés.

    Le nom fourni par le client n'est jamais réutilisé.
    """
    validate_image_upload(upload)
    with Image.open(upload) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
    image.thumbnail(max_size)
    buffer = io.BytesIO()
    image.save(buffer, format="WEBP", quality=85, method=4)
    return ContentFile(buffer.getvalue(), name=f"{uuid.uuid4().hex}.webp")


def replace_image(instance, field_name: str, upload: UploadedFile, *, max_size: tuple[int, int]):
    """Enregistre la nouvelle image puis supprime l'ancien fichier."""
    field = getattr(instance, field_name)
    previous = field.name if field else None
    field.save("image.webp", normalized_image(upload, max_size=max_size), save=False)
    instance.save(update_fields=[field_name, "updated_at"])
    if previous:
        field.storage.delete(previous)
    return instance


def remove_image(instance, field_name: str) -> None:
    field = getattr(instance, field_name)
    if field:
        field.delete(save=False)
        instance.save(update_fields=[field_name, "updated_at"])
