"""Build reports from request filters, and run export jobs."""

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone, translation
from django.utils.text import slugify
from django.utils.translation import gettext as _
from rest_framework import serializers
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.audit import services as audit
from apps.core.tenancy import OrgContext, load_permissions
from apps.events.models import Event
from apps.organizations.models import FinancialYear, Organization, OrganizationMembership

from . import exporters
from .models import ExportJob
from .registry import REPORTS, ReportContext, can_export, can_view

EXPORT = "export"


class ReportFilterSerializer(serializers.Serializer):
    event = serializers.UUIDField(required=False)
    financial_year = serializers.UUIDField(required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    fund = serializers.UUIDField(required=False)
    contribution_type = serializers.UUIDField(required=False)
    collector = serializers.UUIDField(required=False)
    person = serializers.UUIDField(required=False)
    category = serializers.UUIDField(required=False)
    mode = serializers.CharField(required=False, max_length=20)
    status = serializers.CharField(required=False, max_length=20)
    action = serializers.CharField(required=False, max_length=40)

    def validate(self, attrs):
        if attrs.get("date_from") and attrs.get("date_to") and attrs["date_from"] > attrs["date_to"]:
            raise serializers.ValidationError({"date_to": [_("The end date must be after the start date.")]})
        return attrs


def definition_for(report_type, org_context, *, export=False):
    definition = REPORTS.get(report_type)
    if definition is None:
        raise NotFound()
    allowed = can_export(definition, org_context) if export else can_view(definition, org_context)
    if not allowed:
        raise PermissionDenied()
    return definition


def parse_filters(data, definition) -> dict:
    serializer = ReportFilterSerializer(data={k: v for k, v in data.items() if k in definition.filters and v != ""})
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


def build(definition, org_context, filters):
    org = org_context.organization
    events = Event.objects.for_org(org).alive()
    event = None
    if filters.get("event"):
        event = events.filter(pk=filters["event"]).select_related("financial_year").first()
        if event is None:
            raise serializers.ValidationError({"event": [_("Event not found.")]})
        events = events.filter(pk=event.pk)
        scope = f"{event.name} · {event.financial_year.label}"
    else:
        if definition.needs_event:
            raise serializers.ValidationError({"event": [_("Select an event.")]})
        fy_qs = FinancialYear.objects.for_org(org)
        fy = None
        if filters.get("financial_year"):
            fy = fy_qs.filter(pk=filters["financial_year"]).first()
            if fy is None:
                raise serializers.ValidationError({"financial_year": [_("Financial year not found.")]})
        fy = fy or fy_qs.filter(is_current=True).first()
        if fy is not None:
            events = events.filter(financial_year=fy)
            scope = _("Financial year %(label)s") % {"label": fy.label}
        else:
            scope = _("All events")
    if filters.get("date_from") or filters.get("date_to"):
        scope += " · " + " – ".join(
            d.strftime("%d-%m-%Y") if d else "…" for d in (filters.get("date_from"), filters.get("date_to"))
        )
    ctx = ReportContext(
        org=org, events=events, event=event, filters=filters, org_context=org_context, scope_label=scope
    )
    return definition.build(ctx), scope


def start_export(*, org_context, definition, filters, file_format, request):
    job = ExportJob.objects.create(
        organization=org_context.organization,
        requested_by=request.user,
        membership=org_context.membership,
        report_type=definition.key,
        format=file_format,
        filters={k: str(v) for k, v in filters.items()},
        language=translation.get_language() or "en",
        created_by=request.user,
        updated_by=request.user,
    )
    audit.record(
        request=request,
        organization=org_context.organization,
        action=EXPORT,
        entity_type="reports.exportjob",
        entity_id=job.pk,
        after={"report": definition.key, "format": file_format, "filters": job.filters},
    )
    from .tasks import run_export

    run_export.delay(str(job.pk))
    job.refresh_from_db()
    return job


def _context_for(job) -> OrgContext:
    membership = (
        OrganizationMembership.objects.select_related("organization", "role")
        .filter(
            pk=job.membership_id,
            status=OrganizationMembership.Status.ACTIVE,
            organization__status=Organization.Status.ACTIVE,
        )
        .first()
    )
    if membership is None:
        raise PermissionDenied()
    return OrgContext(membership.organization, membership, load_permissions(membership.role))


def run(job: ExportJob):
    """Build the file. Permissions are checked again here, in case they changed since the request."""
    job.status = ExportJob.Status.RUNNING
    job.save(update_fields=["status", "updated_at"])
    try:
        with translation.override(job.language):
            org_context = _context_for(job)
            definition = definition_for(job.report_type, org_context, export=True)
            filters = parse_filters(job.filters, definition)
            report, scope = build(definition, org_context, filters)
            content = exporters.RENDERERS[job.format](report, exporters.meta_for(org_context.organization, scope))
            stamp = timezone.localtime().strftime("%Y%m%d-%H%M")
            job.file_name = f"{slugify(definition.key)}-{stamp}.{job.format}"
            job.file = default_storage.save(
                f"orgs/{job.organization_id}/exports/{job.pk}/{job.file_name}", ContentFile(content)
            )
            job.row_count = len(report.rows)
            job.status = ExportJob.Status.DONE
    except Exception as exc:  # noqa: BLE001 - any failure is reported on the job
        job.status = ExportJob.Status.FAILED
        job.error = str(getattr(exc, "detail", exc))[:300]
    job.finished_at = timezone.now()
    job.save()
    return job
