from typing import Any

from rest_framework import serializers

from apps.accounts.models import User
from apps.community.serializers import AuthorSerializer

from .models import Block, Conversation, Message

HIDDEN_PLACEHOLDER = "Message masqué par la modération."


class MessageSerializer(serializers.ModelSerializer):
    sender = AuthorSerializer(read_only=True)
    content = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ["id", "sender", "content", "is_hidden", "created_at"]
        read_only_fields = fields

    def get_content(self, message: Message) -> str:
        return HIDDEN_PLACEHOLDER if message.is_hidden else message.content


class MessageCreateSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=Message.MAX_LENGTH)


class ConversationStartSerializer(MessageCreateSerializer):
    username = serializers.SlugRelatedField(slug_field="username", queryset=User.objects.all())


class ConversationSerializer(serializers.ModelSerializer):
    other = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ["id", "other", "last_message", "unread_count", "last_message_at", "created_at"]
        read_only_fields = fields

    def _user(self) -> User:
        return self.context["request"].user

    def get_other(self, conversation: Conversation) -> dict[str, Any]:
        participant = next(
            p for p in conversation.participants.all() if p.user_id != self._user().pk
        )
        return AuthorSerializer(participant.user, context=self.context).data

    def get_last_message(self, conversation: Conversation) -> dict[str, Any] | None:
        message = (
            conversation.messages.order_by("-created_at").select_related("sender__profile").first()
        )
        return MessageSerializer(message, context=self.context).data if message else None

    def get_unread_count(self, conversation: Conversation) -> int:
        mine = next(p for p in conversation.participants.all() if p.user_id == self._user().pk)
        messages = conversation.messages.exclude(sender=self._user())
        if mine.last_read_at:
            messages = messages.filter(created_at__gt=mine.last_read_at)
        return messages.count()


class BlockSerializer(serializers.ModelSerializer):
    blocked = AuthorSerializer(read_only=True)

    class Meta:
        model = Block
        fields = ["id", "blocked", "created_at"]
        read_only_fields = fields


class BlockCreateSerializer(serializers.Serializer):
    username = serializers.SlugRelatedField(slug_field="username", queryset=User.objects.all())
