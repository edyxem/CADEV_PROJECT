"""Point d'entrée unique pour créer des notifications."""

from typing import Any

from django.db.models import Model
from django.utils import timezone

from apps.accounts.models import User

from .models import Notification


def notify(
    recipient: User | None,
    *,
    type: str,
    title: str,
    message: str = "",
    actor: User | None = None,
    target: Model | None = None,
    target_url: str = "",
) -> Notification | None:
    """Crée une notification, sauf pour sa propre action ou un compte désactivé.

    Le texte ne doit contenir que des informations déjà visibles par le
    destinataire (titres publics, noms d'utilisateur) : jamais d'e-mail,
    de motif de signalement ni de contenu privé.
    """
    if recipient is None or not recipient.is_active:
        return None
    if actor is not None and actor.pk == recipient.pk:
        return None
    if not _wants(recipient, type):
        return None
    return Notification.objects.create(
        recipient=recipient,
        actor=actor,
        type=type,
        title=title[:140],
        message=message[:300],
        target_type=target._meta.model_name if target is not None else "",
        target_id=getattr(target, "pk", None),
        target_url=target_url,
    )


def _wants(recipient: User, notification_type: str) -> bool:
    """Respecte les préférences du membre lorsqu'elles existent."""
    preferences: Any = getattr(recipient, "notification_preferences", None)
    if preferences is None:
        return True
    return notification_type not in (preferences.muted_types or [])


def mark_read(notification: Notification) -> Notification:
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=["is_read", "read_at", "updated_at"])
    return notification


def mark_all_read(recipient: User) -> int:
    return Notification.objects.filter(recipient=recipient, is_read=False).update(
        is_read=True, read_at=timezone.now()
    )
