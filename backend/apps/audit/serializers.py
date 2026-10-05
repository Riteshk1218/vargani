from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor_user.full_name", default=None, read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "action",
            "entity_type",
            "entity_id",
            "actor_user",
            "actor_name",
            "actor_role_code",
            "before",
            "after",
            "changed_fields",
            "ip",
            "user_agent",
            "request_id",
            "created_at",
        ]
        read_only_fields = fields
