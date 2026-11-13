"""Assainissement des contenus riches saisis par les membres."""

import nh3

ALLOWED_TAGS: set[str] = {
    "a",
    "b",
    "blockquote",
    "br",
    "code",
    "em",
    "h2",
    "h3",
    "h4",
    "hr",
    "i",
    "li",
    "ol",
    "p",
    "pre",
    "s",
    "strong",
    "ul",
}
ALLOWED_ATTRIBUTES: dict[str, set[str]] = {"a": {"href", "title"}, "code": {"class"}}
ALLOWED_URL_SCHEMES: set[str] = {"http", "https", "mailto"}


def sanitize_rich_text(value: str | None) -> str:
    """Ne conserve qu'une liste blanche de balises et de schémas d'URL."""
    if not value:
        return ""
    return nh3.clean(
        value,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=ALLOWED_URL_SCHEMES,
        link_rel="noopener noreferrer nofollow",
    ).strip()


def has_visible_text(value: str | None) -> bool:
    """Vrai si le contenu garde du texte une fois toutes les balises retirées."""
    if not value:
        return False
    return bool(nh3.clean(value, tags=set()).strip())
