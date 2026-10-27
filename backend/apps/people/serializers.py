from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.accounts.serializers import MobileField
from apps.core.serializers import CreatedByMixin

from .models import Person, PersonType


class PersonSerializer(CreatedByMixin, serializers.ModelSerializer):
    mobile = MobileField(required=False, allow_blank=True, allow_null=True)
    alt_mobile = MobileField(required=False, allow_blank=True, allow_null=True)
    person_types = serializers.ListField(child=serializers.ChoiceField(choices=PersonType.choices), required=False)
    has_login = serializers.SerializerMethodField()
    linked_user = serializers.UUIDField(source="user_id", read_only=True, allow_null=True)
    linked_user_name = serializers.SerializerMethodField()

    class Meta:
        model = Person
        fields = [
            "id",
            "full_name",
            "mobile",
            "alt_mobile",
            "email",
            "unit",
            "building",
            "area",
            "address_line",
            "city",
            "pincode",
            "person_types",
            "notes",
            "is_active",
            "has_login",
            "linked_user",
            "linked_user_name",
            "created_at",
            "created_by_name",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "is_active",
            "has_login",
            "linked_user",
            "linked_user_name",
            "created_at",
            "created_by_name",
            "updated_at",
        ]

    def get_has_login(self, obj) -> bool:
        return obj.user_id is not None

    def get_linked_user_name(self, obj) -> str | None:
        return obj.user.full_name if obj.user_id else None

    def validate_full_name(self, value):
        value = " ".join(value.split())
        if not value:
            raise serializers.ValidationError(_("Enter the person's name."))
        return value

    def validate_person_types(self, value):
        return sorted(set(value))

    def to_internal_value(self, data):
        values = super().to_internal_value(data)
        for field in ("mobile", "alt_mobile"):
            if field in values and values[field] is None:
                values[field] = ""
        return values


class PersonSelfSerializer(PersonSerializer):
    """What a member sees about themselves."""

    class Meta(PersonSerializer.Meta):
        fields = ["id", "full_name", "mobile", "email", "unit", "building", "area", "address_line", "city", "pincode"]
        read_only_fields = fields
