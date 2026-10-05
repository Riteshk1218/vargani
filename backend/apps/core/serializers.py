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
