"""Point d'entrée unique pour créer des notifications."""

from typing import Any

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Model
from django.utils import timezone

from apps.accounts.models import User

from .models import MANDATORY_TYPES, Notification


def notify(
    recipient: User | None,
    *,
    type: str,
    title: str,
    message: str = "",
    actor: User | None = None,
    target: Model | None = None,
    target_url: str = "",
    include_inactive: bool = False,
) -> Notification | None:
    """Crée une notification, sauf pour sa propre action ou un compte désactivé.

    Le texte ne doit contenir que des informations déjà visibles par le
    destinataire (titres publics, noms d'utilisateur) : jamais d'e-mail,
    d'identité de signaleur ni de contenu privé. ``include_inactive`` sert aux
    décisions de modération, que le membre suspendu doit pouvoir lire à son retour.
    """
    if recipient is None or (not recipient.is_active and not include_inactive):
        return None
    if actor is not None and actor.pk == recipient.pk:
        return None
    if not _wants(recipient, type):
        return None
    notification = Notification.objects.create(
        recipient=recipient,
        actor=actor,
        type=type,
        title=title[:140],
        message=message[:300],
        target_type=target._meta.model_name if target is not None else "",
        target_id=getattr(target, "pk", None),
        target_url=target_url,
    )
    _maybe_email(recipient, notification)
    return notification


def _wants(recipient: User, notification_type: str) -> bool:
    """Respecte les préférences du membre, sauf pour les notifications obligatoires."""
    if notification_type in MANDATORY_TYPES:
        return True
    try:
        preferences: Any = recipient.notification_preferences
    except ObjectDoesNotExist:
        return True
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


def get_preferences(user: User):
    from .models import NotificationPreference

    preferences, _ = NotificationPreference.objects.get_or_create(user=user)
    return preferences


def _maybe_email(recipient: User, notification: Notification) -> None:
    """Envoie aussi la notification par e-mail si le membre l'a demandé (P2).

    Uniquement vers une adresse vérifiée, après validation de la transaction,
    et sans jamais bloquer l'action en cas d'échec d'envoi.
    """
    if not recipient.email_verified:
        return
    try:
        preferences: Any = recipient.notification_preferences
    except ObjectDoesNotExist:
        return
    if notification.type not in (preferences.email_types or []):
        return

    def send() -> None:
        link = f"{settings.FRONTEND_URL.rstrip('/')}{notification.target_url}"
        body = f"{notification.title}\n\n{notification.message}\n\n{link}\n".strip()
        send_mail(
            notification.title,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [recipient.email],
            fail_silently=True,
        )

    transaction.on_commit(send)
