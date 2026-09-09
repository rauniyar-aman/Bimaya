from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """Read shape for an in-app notification."""

    is_read = serializers.BooleanField(read_only=True)

    class Meta:
        model = Notification
        fields = (
            "id",
            "type",
            "title",
            "body",
            "url",
            "read_at",
            "is_read",
            "created_at",
        )
        read_only_fields = fields


class PushSubscribeSerializer(serializers.Serializer):
    """Validates the browser's native ``PushSubscription`` JSON.

    ``PushSubscription.toJSON()`` yields ``{endpoint, expirationTime, keys:
    {p256dh, auth}}``; we only need the endpoint and the two encryption keys.
    """

    endpoint = serializers.URLField(max_length=500)
    keys = serializers.DictField(child=serializers.CharField())

    def validate_keys(self, value):
        if not value.get("p256dh") or not value.get("auth"):
            raise serializers.ValidationError(
                "Both p256dh and auth keys are required."
            )
        return value


class PushUnsubscribeSerializer(serializers.Serializer):
    """The endpoint identifying the subscription to remove."""

    endpoint = serializers.URLField(max_length=500)
