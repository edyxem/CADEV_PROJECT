"""Règles de la messagerie : blocage, anti-spam, confidentialité."""

import re

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import exceptions

from apps.accounts.models import User
from apps.notifications.models import Notification
from apps.notifications.services import notify
from common.exceptions import BusinessRuleViolation
from common.sanitization import to_plain_text

from .models import Block, Conversation, ConversationParticipant, Message

URL_PATTERN = re.compile(r"\b(?:[a-z][a-z0-9+.-]*):(?://)?\S+", re.IGNORECASE)
MAX_LINKS = 3


def is_blocked_between(first: User, second: User) -> bool:
    return Block.objects.filter(
        Q(blocker=first, blocked=second) | Q(blocker=second, blocked=first)
    ).exists()


def _key(first: User, second: User) -> str:
    return ":".join(sorted([str(first.pk), str(second.pk)]))


def clean_message(content: str) -> str:
    """Texte brut, au plus trois liens, et uniquement en http(s) (§P)."""
    content = to_plain_text(content)
    if not content:
        raise exceptions.ValidationError({"content": ["Le message est vide."]})
    links = URL_PATTERN.findall(content)
    if len(links) > MAX_LINKS:
        raise exceptions.ValidationError(
            {"content": [f"{MAX_LINKS} liens au maximum par message."]}
        )
    if any(not link.lower().startswith(("http://", "https://")) for link in links):
        raise exceptions.ValidationError(
            {"content": ["Seuls les liens http et https sont acceptés."]}
        )
    return content


def other_participant(conversation: Conversation, user: User) -> User:
    return conversation.participants.exclude(user=user).select_related("user").get().user


@transaction.atomic
def start_conversation(
    *, sender: User, recipient: User, content: str
) -> tuple[Conversation, Message]:
    if recipient.pk == sender.pk:
        raise BusinessRuleViolation(
            "Vous ne pouvez pas vous écrire à vous-même.", code="self_message"
        )
    if not recipient.is_active:
        raise BusinessRuleViolation("Ce compte n'est plus actif.", code="inactive_account")
    conversation, created = Conversation.objects.get_or_create(
        participants_key=_key(sender, recipient)
    )
    if created:
        ConversationParticipant.objects.bulk_create(
            [
                ConversationParticipant(conversation=conversation, user=sender),
                ConversationParticipant(conversation=conversation, user=recipient),
            ]
        )
    return conversation, send_message(conversation=conversation, sender=sender, content=content)


@transaction.atomic
def send_message(*, conversation: Conversation, sender: User, content: str) -> Message:
    if not conversation.participants.filter(user=sender).exists():
        raise exceptions.NotFound()
    recipient = other_participant(conversation, sender)
    if is_blocked_between(sender, recipient):
        raise BusinessRuleViolation("Vous ne pouvez pas écrire à ce membre.", code="blocked")
    message = Message.objects.create(
        conversation=conversation, sender=sender, content=clean_message(content)
    )
    now = timezone.now()
    Conversation.objects.filter(pk=conversation.pk).update(last_message_at=now)
    ConversationParticipant.objects.filter(conversation=conversation, user=sender).update(
        last_read_at=now
    )
    # Une seule notification non lue par conversation, pour éviter le bruit.
    pending = Notification.objects.filter(
        recipient=recipient,
        type=Notification.Type.MESSAGE_RECEIVED,
        target_id=conversation.pk,
        is_read=False,
    ).exists()
    if not pending:
        notify(
            recipient,
            type=Notification.Type.MESSAGE_RECEIVED,
            title=f"Nouveau message de {sender.username}",
            actor=sender,
            target=conversation,
            target_url=f"/messages/{conversation.pk}",
        )
    return message


def mark_read(*, conversation: Conversation, user: User) -> None:
    now = timezone.now()
    ConversationParticipant.objects.filter(conversation=conversation, user=user).update(
        last_read_at=now
    )
    Notification.objects.filter(
        recipient=user,
        type=Notification.Type.MESSAGE_RECEIVED,
        target_id=conversation.pk,
        is_read=False,
    ).update(is_read=True, read_at=now)


def block(*, blocker: User, blocked: User) -> Block:
    if blocker.pk == blocked.pk:
        raise BusinessRuleViolation("Vous ne pouvez pas vous bloquer vous-même.", code="self_block")
    try:
        with transaction.atomic():
            return Block.objects.create(blocker=blocker, blocked=blocked)
    except IntegrityError as exc:
        raise BusinessRuleViolation("Ce membre est déjà bloqué.", code="already_blocked") from exc
