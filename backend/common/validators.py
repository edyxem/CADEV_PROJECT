"""Validateurs réutilisables : URLs externes et images téléversées."""

from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from PIL import Image, UnidentifiedImageError

ALLOWED_IMAGE_FORMATS = {"JPEG": {".jpg", ".jpeg"}, "PNG": {".png"}, "WEBP": {".webp"}}
MAX_IMAGE_PIXELS = 4096


def validate_http_url(value: str) -> None:
    """Refuse tout schéma autre que http/https (javascript:, data:, etc.)."""
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValidationError(
            "L'URL doit être absolue et utiliser le schéma http ou https.", code="invalid_url"
        )


def validate_image_upload(file: UploadedFile) -> None:
    """Contrôle la taille, l'extension et le contenu réel d'une image."""
    if file.size > settings.MAX_IMAGE_UPLOAD_BYTES:
        max_mb = settings.MAX_IMAGE_UPLOAD_BYTES / (1024 * 1024)
        raise ValidationError(
            f"Image trop lourde (maximum {max_mb:.0f} Mo).", code="file_too_large"
        )

    extension = "." + file.name.rsplit(".", 1)[-1].lower() if "." in file.name else ""
    try:
        file.seek(0)
        with Image.open(file) as image:
            image.verify()
            image_format = image.format
            width, height = image.size
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
        raise ValidationError(
            "Le fichier n'est pas une image valide.", code="invalid_image"
        ) from exc
    finally:
        file.seek(0)

    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise ValidationError("Formats acceptés : JPEG, PNG, WebP.", code="invalid_image_type")
    if extension not in ALLOWED_IMAGE_FORMATS[image_format]:
        raise ValidationError(
            "L'extension du fichier ne correspond pas à son contenu.", code="invalid_extension"
        )
    if width > MAX_IMAGE_PIXELS or height > MAX_IMAGE_PIXELS:
        raise ValidationError(
            f"Dimensions maximales : {MAX_IMAGE_PIXELS}×{MAX_IMAGE_PIXELS} px.",
            code="image_too_large",
        )
