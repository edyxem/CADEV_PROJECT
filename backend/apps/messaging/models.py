"""Messagerie privée entre deux membres, sans temps réel (P2, module P)."""

from django.conf import settings
from django.db import models
from django.db.models import F, Q

from common.models import BaseModel


class Block(BaseModel):
    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocks_given"
    )
    blocked = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocks_received"
    )

    class Meta:
        verbose_name = "blocage"
        verbose_name_plural = "blocages"
        constraints = [
            models.UniqueConstraint(fields=["blocker", "blocked"], name="block_unique"),
            models.CheckConstraint(condition=~Q(blocker=F("blocked")), name="block_not_self"),
        ]


class Conversation(BaseModel):
    # Clé « uuid_min:uuid_max » : une seule conversation par couple de membres.
    participants_key = models.CharField(max_length=80, unique=True)
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        verbose_name = "conversation"
        verbose_name_plural = "conversations"
        ordering = ["-last_message_at", "-created_at"]


class ConversationParticipant(BaseModel):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="participants"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversation_memberships"
    )
    last_read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "participant"
        verbose_name_plural = "participants"
        constraints = [
            models.UniqueConstraint(fields=["conversation", "user"], name="participant_unique"),
        ]


class Message(BaseModel):
    MAX_LENGTH = 2000

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages"
    )
    content = models.TextField(max_length=MAX_LENGTH)
    is_hidden = models.BooleanField("masqué par la modération", default=False)

    class Meta:
        verbose_name = "message"
        verbose_name_plural = "messages"
        ordering = ["created_at"]
        indexes = [models.Index(fields=["conversation", "created_at"], name="message_thread_idx")]
