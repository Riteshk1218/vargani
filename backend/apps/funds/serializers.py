from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.core.fields import TenantPrimaryKeyRelatedField
from apps.core.serializers import ImmutableFieldsMixin
from apps.events.models import Event

from .models import Fund


class FundSerializer(ImmutableFieldsMixin, serializers.ModelSerializer):
    event = TenantPrimaryKeyRelatedField(queryset=Event.objects.filter(deleted_at__isnull=True))

    class Meta:
        model = Fund
        fields = ["id", "event", "name", "description", "target_amount", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        value = " ".join(value.split())
        if not value:
            raise serializers.ValidationError(_("Enter a name."))
        return value

    def validate_target_amount(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError(_("Amount must be more than zero."))
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        event = attrs.get("event", getattr(self.instance, "event", None))
        name = attrs.get("name", getattr(self.instance, "name", None))
        siblings = Fund.objects.filter(event=event, name__iexact=name)
        if self.instance:
            siblings = siblings.exclude(pk=self.instance.pk)
        if siblings.exists():
            raise serializers.ValidationError({"name": [_("This event already has a fund with this name.")]})
        return attrs
