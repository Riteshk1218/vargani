from rest_framework import serializers

from .models import DeviceToken, Notification
from .templates import render


class NotificationSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    body = serializers.SerializerMethodField()
    organization_name = serializers.CharField(source="organization.name", default=None, read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "type",
            "title",
            "body",
            "organization",
            "organization_name",
            "entity_type",
            "entity_id",
            "link",
            "read_at",
            "created_at",
        ]
        read_only_fields = fields

    def _rendered(self, obj):
        cache = self.context.setdefault("_rendered", {})
        if obj.pk not in cache:
            cache[obj.pk] = render(obj, getattr(obj.recipient, "preferred_language", None))
        return cache[obj.pk]

    def get_title(self, obj) -> str:
        return self._rendered(obj)[0]

    def get_body(self, obj) -> str:
        return self._rendered(obj)[1]


class AnnouncementSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=120)
    message = serializers.CharField(max_length=1000)


class DeviceSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=512)
    platform = serializers.ChoiceField(choices=DeviceToken.Platform.choices, default=DeviceToken.Platform.ANDROID)
    app_version = serializers.CharField(max_length=40, required=False, allow_blank=True, default="")


class DeviceTokenSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=512)
