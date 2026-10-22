"""Download any list as CSV or Excel: GET /<list>/download/?file=csv|xlsx plus the list's own filters.

The rows are exactly what the caller can see in that list (same queryset, filters, search and data scope),
written with the report exporters. Downloading needs the "reports.export" permission, which the
Organization Admin can switch on or off for each person (OrganizationMembership.can_download).
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.translation import gettext as _
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.audit import services as audit

from .tenancy import DOWNLOAD_PERMISSION

MAX_ROWS = 50_000
FILE_TYPES = ("csv", "xlsx")


@dataclass
class Col:
    key: str  # serializer field; "a.b" reads a nested value
    label: str  # gettext_noop'd, translated when the file is made
    kind: str = "text"  # text | money | number | date | datetime | mode | status | source | bool


def _pick(data, key):
    for part in key.split("."):
        if not isinstance(data, dict):
            return None
        data = data.get(part)
    return data


def _value(raw, kind):
    from apps.reports.registry import SOURCE_LABELS, mode_label, status_label

    if raw is None or raw == "":
        return None
    if kind == "money":
        try:
            return Decimal(str(raw))
        except InvalidOperation:
            return raw
    if kind == "date":
        return parse_date(str(raw)[:10]) or raw
    if kind == "datetime":
        parsed = parse_datetime(str(raw))
        return timezone.localtime(parsed).replace(tzinfo=None) if parsed and timezone.is_aware(parsed) else raw
    if kind == "mode":
        return mode_label(raw)
    if kind == "status":
        return status_label(raw)
    if kind == "source":
        return _(SOURCE_LABELS.get(raw, raw))
    if kind == "bool":
        return _("Yes") if raw else _("No")
    if isinstance(raw, list):
        return ", ".join(str(item) for item in raw)
    if isinstance(raw, date | datetime | Decimal | int | float):
        return raw
    return str(raw)


class ListDownloadMixin:
    """Add to a tenant list viewset and set `download_title` and `download_columns`."""

    download_title = ""
    download_columns: list[Col] = []

    def get_required_permissions(self):
        if getattr(self, "action", None) == "download":
            return self.required_permissions.get("list")
        return super().get_required_permissions()

    @extend_schema(
        parameters=[OpenApiParameter("file", OpenApiTypes.STR, enum=FILE_TYPES, description="csv (default) or xlsx")],
        responses={(200, "application/octet-stream"): OpenApiTypes.BINARY},
    )
    @action(detail=False, methods=["get"])
    def download(self, request):
        """The list as a CSV or Excel file, with the same filters and search as the list."""
        from apps.reports import exporters
        from apps.reports.registry import Column, Report

        context = self.org_context
        if not context.has(DOWNLOAD_PERMISSION):
            raise PermissionDenied(_("Ask the Organization Admin to allow you to download lists."))
        file_type = request.query_params.get("file", "csv")
        if file_type not in FILE_TYPES:
            raise ValidationError({"file": [_("Choose csv or xlsx.")]})
        queryset = self.filter_queryset(self.get_queryset())
        items = list(queryset[: MAX_ROWS + 1])
        if len(items) > MAX_ROWS:
            raise ValidationError({"file": [_("Too many rows. Narrow the list with the filters first.")]})
        data = self.get_serializer(items, many=True).data
        columns = [
            Column(f"c{i}", _(c.label), c.kind if c.kind in ("money", "number", "date", "datetime") else "text")
            for i, c in enumerate(self.download_columns)
        ]
        rows = [
            {f"c{i}": _value(_pick(row, c.key), c.kind) for i, c in enumerate(self.download_columns)} for row in data
        ]
        title = _(self.download_title)
        report = Report(title, columns, rows)
        content = exporters.RENDERERS[file_type](
            report, exporters.meta_for(context.organization, self.download_scope())
        )
        audit.record(
            request=request,
            organization=context.organization,
            action="export",
            entity_type=f"list.{self.basename}",
            after={"format": file_type, "rows": len(rows), "filters": request.query_params.dict()},
        )
        stamp = timezone.localtime().strftime("%Y%m%d-%H%M")
        response = HttpResponse(content, content_type=exporters.CONTENT_TYPES[file_type])
        response["Content-Disposition"] = f'attachment; filename="{self.basename}-{stamp}.{file_type}"'
        response["Cache-Control"] = "no-store"
        return response

    def download_scope(self) -> str:
        """A line under the title saying what the file covers (the event, when the list is filtered by one)."""
        from apps.events.models import Event

        event_id = self.request.query_params.get("event")
        if event_id:
            event = Event.objects.for_org(self.organization).filter(pk=event_id).first()
            if event is not None:
                return event.name
        return _("All events")
