from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.core.fields import TenantPrimaryKeyRelatedField
from apps.core.serializers import CreatedByMixin, ImmutableFieldsMixin
from apps.events.models import Event
from apps.funds.models import Fund
from apps.organizations.models import OrganizationMembership
from apps.people.models import Person

from .models import CollectorAssignment, Contribution, ContributionType, Due


class ContributionTypeSerializer(ImmutableFieldsMixin, serializers.ModelSerializer):
    event = TenantPrimaryKeyRelatedField(queryset=Event.objects.filter(deleted_at__isnull=True))
    fund = TenantPrimaryKeyRelatedField(queryset=Fund.objects.all(), required=False, allow_null=True)
    fund_name = serializers.CharField(source="fund.name", read_only=True, default=None)

    class Meta:
        model = ContributionType
        fields = [
            "id",
            "event",
            "fund",
            "fund_name",
            "name",
            "kind",
            "suggested_min",
            "suggested_max",
            "target_amount",
            "is_mandatory",
            "start_date",
            "end_date",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "fund_name", "created_at", "updated_at"]

    def validate_name(self, value):
        value = " ".join(value.split())
        if not value:
            raise serializers.ValidationError(_("Enter a name."))
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        instance = self.instance

        def current(field):
            return attrs.get(field, getattr(instance, field, None))

        event, fund = current("event"), current("fund")
        if fund is not None and fund.event_id != event.pk:
            raise serializers.ValidationError({"fund": [_("This fund belongs to another event.")]})
        for field in ("suggested_min", "suggested_max", "target_amount"):
            value = attrs.get(field)
            if value is not None and value <= 0:
                raise serializers.ValidationError({field: [_("Amount must be more than zero.")]})
        low, high = current("suggested_min"), current("suggested_max")
        if low is not None and high is not None and low > high:
            raise serializers.ValidationError({"suggested_max": [_("Maximum must be at least the minimum.")]})
        if current("is_mandatory") and current("target_amount") is None:
            raise serializers.ValidationError({"target_amount": [_("Enter the amount expected from each person.")]})
        start, end = current("start_date"), current("end_date")
        if start and end and end < start:
            raise serializers.ValidationError({"end_date": [_("End date must be on or after the start date.")]})
        if instance and "kind" in attrs and attrs["kind"] != instance.kind and instance.contributions.exists():
            raise serializers.ValidationError({"kind": [_("This cannot be changed after collections exist.")]})

        siblings = ContributionType.objects.filter(event=event, name__iexact=current("name"))
        if instance:
            siblings = siblings.exclude(pk=instance.pk)
        if siblings.exists():
            raise serializers.ValidationError(
                {"name": [_("This event already has a contribution type with this name.")]}
            )
        return attrs


class ContributionSerializer(CreatedByMixin, serializers.ModelSerializer):
    person_name = serializers.CharField(source="payment.payer_name", read_only=True)
    contribution_type_name = serializers.CharField(source="contribution_type.name", read_only=True)
    fund_name = serializers.CharField(source="fund.name", read_only=True, default=None)
    mode = serializers.CharField(source="payment.mode", read_only=True)
    collector_name = serializers.SerializerMethodField()

    class Meta:
        model = Contribution
        fields = [
            "id",
            "event",
            "person",
            "person_name",
            "contribution_type",
            "contribution_type_name",
            "fund",
            "fund_name",
            "payment",
            "mode",
            "period_month",
            "amount",
            "contributed_on",
            "status",
            "collector_name",
            "notes",
            "created_at",
            "created_by_name",
        ]
        read_only_fields = fields

    def get_collector_name(self, obj) -> str | None:
        return obj.collector.user.full_name if obj.collector else None


class CollectorAssignmentSerializer(serializers.ModelSerializer):
    person_name = serializers.CharField(source="person.full_name", read_only=True)
    person_mobile = serializers.CharField(source="person.mobile", read_only=True)
    person_area = serializers.CharField(source="person.area", read_only=True)
    collector_name = serializers.CharField(source="collector.user.full_name", read_only=True)

    class Meta:
        model = CollectorAssignment
        fields = [
            "id",
            "event",
            "collector",
            "collector_name",
            "person",
            "person_name",
            "person_mobile",
            "person_area",
            "is_active",
            "active_from",
            "active_to",
        ]
        read_only_fields = fields


class AssignInputSerializer(serializers.Serializer):
    event = TenantPrimaryKeyRelatedField(queryset=Event.objects.filter(deleted_at__isnull=True))
    collector = TenantPrimaryKeyRelatedField(queryset=OrganizationMembership.objects.filter(status="active"))
    people = TenantPrimaryKeyRelatedField(
        queryset=Person.objects.filter(deleted_at__isnull=True), many=True, allow_empty=False
    )

    def validate_people(self, value):
        if len(value) > 500:
            raise serializers.ValidationError(_("Assign at most 500 people at a time."))
        return value


class DueSerializer(CreatedByMixin, serializers.ModelSerializer):
    person_name = serializers.CharField(source="person.full_name", read_only=True)
    person_mobile = serializers.CharField(source="person.mobile", read_only=True)
    contribution_type_name = serializers.CharField(source="contribution_type.name", read_only=True)
    collector_name = serializers.SerializerMethodField()
    paid = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    remaining = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    receipt_number = serializers.CharField(read_only=True, allow_null=True)

    class Meta:
        model = Due
        fields = [
            "id",
            "event",
            "person",
            "person_name",
            "person_mobile",
            "contribution_type",
            "contribution_type_name",
            "period_month",
            "amount",
            "paid",
            "remaining",
            "status",
            "status_reason",
            "payment",
            "receipt_number",
            "collector_name",
            "created_at",
            "created_by_name",
        ]
        read_only_fields = fields

    def get_collector_name(self, obj) -> str | None:
        return obj.collector.user.full_name if obj.collector_id else None


class DueCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=300)
