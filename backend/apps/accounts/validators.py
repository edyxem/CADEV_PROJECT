"""Format documenté du nom d'utilisateur."""

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

USERNAME_REGEX = r"^[a-zA-Z][a-zA-Z0-9_]{2,29}$"
USERNAME_HELP = (
    "3 à 30 caractères : lettres non accentuées, chiffres et tiret bas, "
    "en commençant par une lettre."
)
RESERVED_USERNAMES = frozenset(
    {
        "admin",
        "administrator",
        "afridev",
        "api",
        "me",
        "moderator",
        "null",
        "root",
        "support",
        "system",
        "undefined",
    }
)

username_format_validator = RegexValidator(
    regex=USERNAME_REGEX, message=USERNAME_HELP, code="invalid_username"
)


def validate_username_not_reserved(value: str) -> None:
    """Empêche l'usurpation de noms techniques ou de routes (``me``)."""
    if value.lower() in RESERVED_USERNAMES:
        raise ValidationError("Ce nom d'utilisateur est réservé.", code="reserved_username")
