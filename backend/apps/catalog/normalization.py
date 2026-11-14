"""Normalisation des libellés de référentiel pour éviter les doublons de casse ou d'écriture."""

import re

from django.utils.text import slugify

_SYMBOLS = (("c++", "cpp"), ("++", "pp"), ("#", "sharp"), ("+", "plus"))


def normalize_label(value: str) -> str:
    """Supprime les espaces superflus : « Node.js  » → « Node.js »."""
    return re.sub(r"\s+", " ", (value or "").strip())


def make_slug(value: str) -> str:
    """Slug stable qui distingue « C », « C++ » et « C# », ou « .NET » et « Net »."""
    text = normalize_label(value).lower()
    for symbol, replacement in _SYMBOLS:
        text = text.replace(symbol, replacement)
    if text.startswith("."):
        text = f"dot{text[1:]}"
    text = text.replace(".", "")
    return slugify(text)
