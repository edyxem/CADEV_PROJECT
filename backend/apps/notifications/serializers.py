from rest_framework import serializers

from .models import Notification


class ActorSerializer(serializers.Serializer):
    username = serializers.CharField()


class NotificationSerializer(serializers.ModelSerializer):
    actor = ActorSerializer(read_only=True, allow_null=True)
    type_label = serializers.CharField(source="get_type_display", read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "type",
            "type_label",
            "title",
            "message",
            "actor",
            "target_type",
            "target_id",
            "target_url",
            "is_read",
            "read_at",
            "created_at",
        ]
        read_only_fields = fields


class UnreadCountSerializer(serializers.Serializer):
    unread = serializers.IntegerField()


class MarkedSerializer(serializers.Serializer):
    updated = serializers.IntegerField()
