"""Calendar days in the organization's own time zone, so "27 Oct" means the same day everywhere.

Datetimes (paid_at, issued_at, created_at) are stored in UTC; a payment taken at 1 a.m. in India must still
count on that Indian day in the lists, their filters and the dashboard.
"""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import django_filters
from django.utils import timezone


def org_tz(org):
    try:
        return ZoneInfo(org.timezone)
    except Exception:  # noqa: BLE001
        return timezone.get_current_timezone()


def day_start(org, day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=org_tz(org))


def filter_days(queryset, field: str, org, date_from: date | None = None, date_to: date | None = None):
    """Rows whose `field` falls on date_from..date_to (both included). A date field is compared directly."""
    is_datetime = queryset.model._meta.get_field(field.split("__")[0]).get_internal_type() == "DateTimeField"
    if date_from:
        queryset = queryset.filter(**{f"{field}__gte": day_start(org, date_from) if is_datetime else date_from})
    if date_to:
        if is_datetime:
            queryset = queryset.filter(**{f"{field}__lt": day_start(org, date_to + timedelta(days=1))})
        else:
            queryset = queryset.filter(**{f"{field}__lte": date_to})
    return queryset


class OrgDayFilter(django_filters.DateFilter):
    """`date_from` / `date_to` on a datetime field, by the organization's calendar day."""

    def __init__(self, *args, end: bool = False, **kwargs):
        self.end = end
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value in (None, ""):
            return qs
        org = self.parent.request._org_context.organization
        if self.end:
            return filter_days(qs, self.field_name, org, date_to=value)
        return filter_days(qs, self.field_name, org, date_from=value)
