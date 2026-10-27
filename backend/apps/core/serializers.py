from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class ImmutableFieldsMixin:
    """Rejects changes to the listed fields on update (e.g. which event a record belongs to)."""

    immutable_fields: tuple[str, ...] = ("event",)

    def validate(self, attrs):
        if self.instance is not None:
            for field in self.immutable_fields:
                if field in attrs and attrs[field] != getattr(self.instance, field):
                    raise serializers.ValidationError({field: [_("This cannot be changed.")]})
        return super().validate(attrs)


class CreatedByMixin(serializers.Serializer):
    """Adds `created_by_name`: who made the record, shown with `created_at` in every list."""

    created_by_name = serializers.SerializerMethodField()

    def get_created_by_name(self, obj) -> str | None:
        user = getattr(obj, "created_by", None)
        return (user.full_name or user.username) if user else None
