import re

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.core.fields import TenantPrimaryKeyRelatedField
from apps.core.serializers import CreatedByMixin
from apps.organizations.models import FinancialYear
from apps.people.models import Person

from .models import Event, EventParticipant
from .templates import MODULE_KEYS, TEMPLATES


def suggest_code(name: str) -> str:
    words = [w for w in re.split(r"[^A-Za-z]+", name) if w]
    code = "".join(w[0] for w in words).upper()[:6]
    return code or "EV"


class EventSerializer(CreatedByMixin, serializers.ModelSerializer):
    financial_year = TenantPrimaryKeyRelatedField(queryset=FinancialYear.objects.all())
    financial_year_label = serializers.CharField(source="financial_year.label", read_only=True)
    code = serializers.CharField(max_length=12, required=False, allow_blank=True)

    class Meta:
        model = Event
        fields = [
            "id",
            "name",
            "template",
            "code",
            "financial_year",
            "financial_year_label",
            "start_date",
            "end_date",
            "status",
            "modules",
            "target_amount",
            "description",
            "thank_you_message",
            "created_at",
            "created_by_name",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "financial_year_label", "created_at", "created_by_name", "updated_at"]

    def validate_name(self, value):
        value = " ".join(value.split())
        if not value:
            raise serializers.ValidationError(_("Enter the event name."))
        return value

    def validate_code(self, value):
        value = (value or "").strip().upper()
        if value and not re.fullmatch(r"[A-Z0-9]{1,12}", value):
            raise serializers.ValidationError(_("Use only letters and numbers."))
        return value

    def validate_modules(self, value):
        if not isinstance(value, dict) or any(
            k not in MODULE_KEYS or not isinstance(v, bool) for k, v in value.items()
        ):
            raise serializers.ValidationError(_("Unknown module or invalid value."))
        return value

    def validate(self, attrs):
        org = self.context["organization"]
        instance = self.instance
        fy = attrs.get("financial_year", instance.financial_year if instance else None)
        if instance and "financial_year" in attrs and attrs["financial_year"] != instance.financial_year:
            raise serializers.ValidationError(
                {"financial_year": [_("An event cannot move to another financial year.")]}
            )
        if fy and fy.status == FinancialYear.Status.CLOSED and not instance:
            raise serializers.ValidationError({"financial_year": [_("This financial year is closed.")]})
        start = attrs.get("start_date", instance.start_date if instance else None)
        end = attrs.get("end_date", instance.end_date if instance else None)
        if start and end and end < start:
            raise serializers.ValidationError({"end_date": [_("End date must be on or after the start date.")]})

        template = attrs.get("template", instance.template if instance else "custom")
        if not instance:
            attrs["modules"] = {**TEMPLATES[template]["modules"], **attrs.get("modules", {})}
        elif "modules" in attrs:
            attrs["modules"] = {**instance.modules, **attrs["modules"]}

        siblings = Event.objects.for_org(org).filter(financial_year=fy)
        if instance:
            siblings = siblings.exclude(pk=instance.pk)
        code = attrs.get("code") if "code" in attrs else (instance.code if instance else "")
        if not code:
            base = suggest_code(attrs.get("name", instance.name if instance else ""))
            code, n = base, 2
            while siblings.filter(code=code).exists():
                code, n = f"{base}{n}", n + 1
            attrs["code"] = code
        elif siblings.filter(code=code).exists():
            raise serializers.ValidationError({"code": [_("Another event in this financial year uses this code.")]})
        return attrs


class EventParticipantSerializer(serializers.ModelSerializer):
    event = TenantPrimaryKeyRelatedField(queryset=Event.objects.filter(deleted_at__isnull=True))
    person = TenantPrimaryKeyRelatedField(queryset=Person.objects.filter(deleted_at__isnull=True))
    person_name = serializers.CharField(source="person.full_name", read_only=True)
    person_mobile = serializers.CharField(source="person.mobile", read_only=True)

    class Meta:
        model = EventParticipant
        fields = [
            "id",
            "event",
            "person",
            "person_name",
            "person_mobile",
            "participation_role",
            "status",
            "notes",
            "created_at",
        ]
        read_only_fields = ["id", "person_name", "person_mobile", "created_at"]

    def validate(self, attrs):
        if self.instance:
            for field in ("event", "person"):
                if field in attrs and attrs[field] != getattr(self.instance, field):
                    raise serializers.ValidationError({field: [_("This cannot be changed.")]})
            return attrs
        if EventParticipant.objects.filter(event=attrs["event"], person=attrs["person"]).exists():
            raise serializers.ValidationError(_("This person is already part of the event."))
        return attrs
