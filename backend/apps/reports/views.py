from decimal import Decimal

from django.core.files.storage import default_storage
from django.http import FileResponse
from django.utils.translation import gettext as _
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle, UserRateThrottle
from rest_framework.views import APIView

from apps.contributions.models import Contribution
from apps.contributions.selectors import summarize
from apps.core.permissions import HasOrgPermission
from apps.core.tenancy import SCOPE_ALL
from apps.events.models import Event, EventParticipant
from apps.expenses.models import Expense
from apps.organizations.models import FinancialYear, OrganizationMembership
from apps.payments.models import Payment
from apps.people.models import Person

from . import exporters, services
from . import selectors as sel
from .models import ExportJob
from .registry import REPORTS, can_export, can_view

JSON_ROW_LIMIT = 1000


class DashboardSummaryView(APIView):
    """Dashboard numbers for the active organization (and event, when given).

    Only real numbers are returned. `financial` is present for roles with dashboard.view_financial and covers
    the selected event, or every event of the current financial year when no event is given. Income is
    confirmed contributions plus recorded other income; expenses are approved expenses (reports/selectors.py).
    """

    permission_classes = [IsAuthenticated, HasOrgPermission]

    def get_organization_id(self):
        return None

    def get_required_permissions(self):
        return "events.view"

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        context = request._org_context
        org = context.organization
        events = Event.objects.for_org(org).alive()
        if context.scope("events.view") != SCOPE_ALL:
            events = events.filter(participants__person__user=request.user).distinct()
        data = {
            "events": {
                "total": events.count(),
                "active": events.filter(status=Event.Status.ACTIVE).count(),
            },
            "current_financial_year": None,
            "financial": None,
        }
        fy = FinancialYear.objects.for_org(org).filter(is_current=True).first()
        if fy:
            data["current_financial_year"] = {"id": str(fy.pk), "label": fy.label}
        if context.scope("people.view") == SCOPE_ALL:
            people = Person.objects.for_org(org).alive()
            data["people"] = {"total": people.count(), "active": people.filter(is_active=True).count()}
        if context.has("members.view"):
            data["members"] = {
                "total": OrganizationMembership.objects.filter(
                    organization=org, status=OrganizationMembership.Status.ACTIVE
                ).count()
            }
        event_id = request.query_params.get("event")
        if event_id:
            event = events.filter(pk=event_id).first()
            if event is None:
                raise NotFound()
            data["event"] = {
                "id": str(event.pk),
                "name": event.name,
                "status": event.status,
                "target_amount": str(event.target_amount) if event.target_amount is not None else None,
                "participants": EventParticipant.objects.for_org(org).filter(event=event).count()
                if context.scope("events.view") == SCOPE_ALL
                else None,
            }
        if context.has("dashboard.view_financial"):
            data["financial"] = self._financial(org, event if event_id else None, fy)
        return Response(data)

    def _financial(self, org, event, fy):
        events = Event.objects.for_org(org).alive()
        if event is not None:
            events = events.filter(pk=event.pk)
        elif fy is not None:
            events = events.filter(financial_year=fy)
        else:
            events = events.none()
        lines = Contribution.objects.for_org(org).filter(event__in=events)
        payments = Payment.objects.for_org(org).filter(event__in=events)
        data = summarize(lines, payments)
        targets = [e.target_amount for e in events if e.target_amount is not None]
        data["target_amount"] = f"{sum(targets):.2f}" if targets else None
        data["pending_payments"] = payments.filter(status=Payment.Status.PENDING).count()
        totals = sel.finance_totals(org, events)
        data["other_income"] = sel.money(totals["other_income"])
        data["income"] = sel.money(totals["income"])
        data["expenses"] = sel.money(totals["expenses"])
        data["balance"] = sel.money(totals["balance"])
        data["expenses_by_category"] = [
            {"id": str(r["category"]), "name": r["category__name"], "total": sel.money(r["total"])}
            for r in sel.expenses_by_category(org, events)
        ]
        data["expenses_by_month"] = [
            {"month": r["month"].strftime("%Y-%m"), "total": sel.money(r["total"])}
            for r in sel.expenses_by_month(org, events)
        ]
        data["pending_expenses"] = (
            Expense.objects.for_org(org).filter(event__in=events, status=Expense.Status.SUBMITTED).count()
        )
        data["recent_payments"] = [
            {
                "id": str(p.pk),
                "payer_name": p.payer_name,
                "amount": f"{p.amount:.2f}",
                "mode": p.mode,
                "paid_at": p.paid_at.isoformat(),
                "receipt_number": next((r.receipt_number for r in p.receipts.all() if r.status == "issued"), None),
            }
            for p in payments.filter(status=Payment.Status.SUCCESSFUL)
            .select_related("payer")
            .prefetch_related("receipts")
            .order_by("-paid_at")[:5]
        ]
        return data


class FinancialSummaryView(APIView):
    """Financial summary for the active organization: one row per event, never mixing events or years.

    Collection − Approved expenses (+ other income) = Balance. Filter with `financial_year` and/or `event`;
    without a filter every event of every financial year is listed, newest year first.
    """

    permission_classes = [IsAuthenticated, HasOrgPermission]

    def get_organization_id(self):
        return None

    def get_required_permissions(self):
        return ("dashboard.view_financial", "reports.view_financial")

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        org = request._org_context.organization
        events = Event.objects.for_org(org).alive()
        if request.query_params.get("financial_year"):
            events = events.filter(financial_year_id=request.query_params["financial_year"])
        if request.query_params.get("event"):
            events = events.filter(pk=request.query_params["event"])
        rows = sel.event_summaries(org, events)
        total = {
            key: sel.money(sum((Decimal(r[key]) for r in rows), Decimal(0)))
            for key in (
                "collection",
                "other_income",
                "approved_expenses",
                "pending_expenses",
                "rejected_expenses",
                "balance",
            )
        }
        return Response({"organization": {"id": str(org.pk), "name": org.name}, "events": rows, "total": total})


class ReportViewMixin:
    permission_classes = [IsAuthenticated, HasOrgPermission]

    def get_organization_id(self):
        return None

    def get_required_permissions(self):
        return ("reports.view_general", "reports.view_financial", "audit.view")


class ReportListView(ReportViewMixin, APIView):
    """Reports available to my role, with the filters each accepts."""

    @extend_schema(responses=OpenApiTypes.OBJECT, operation_id="reports_list")
    def get(self, request):
        context = request._org_context
        return Response(
            [
                {
                    "type": d.key,
                    "title": _(d.title),
                    "group": d.group,
                    "filters": list(d.filters),
                    "needs_event": d.needs_event,
                    "can_export": can_export(d, context),
                }
                for d in REPORTS.values()
                if can_view(d, context)
            ]
        )


class ReportView(ReportViewMixin, APIView):
    """One report as JSON (first 1,000 rows; export for the rest). Filters are query parameters."""

    throttle_classes = [UserRateThrottle, ScopedRateThrottle]
    throttle_scope = "reports"

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request, report_type):
        context = request._org_context
        definition = services.definition_for(report_type, context)
        report, scope = services.build(definition, context, services.parse_filters(request.query_params, definition))
        return Response({**exporters.as_json(report, JSON_ROW_LIMIT), "scope": scope, "type": definition.key})


class ExportRequestSerializer(serializers.Serializer):
    format = serializers.ChoiceField(choices=ExportJob.Format.choices)
    filters = serializers.DictField(required=False, default=dict)


class ExportJobSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = ExportJob
        fields = [
            "id",
            "report_type",
            "format",
            "status",
            "file_name",
            "row_count",
            "error",
            "created_at",
            "finished_at",
            "download_url",
        ]
        read_only_fields = fields

    def get_download_url(self, obj) -> str | None:
        if obj.status != ExportJob.Status.DONE:
            return None
        return f"/api/v1/exports/{obj.pk}/download/"


class ReportExportView(ReportViewMixin, APIView):
    """Start an export (CSV, Excel or PDF). Poll GET /exports/{id}/ until `status` is done, then download."""

    throttle_classes = [UserRateThrottle, ScopedRateThrottle]
    throttle_scope = "exports"

    def get_required_permissions(self):
        return "reports.export"

    @extend_schema(request=ExportRequestSerializer, responses={202: ExportJobSerializer})
    def post(self, request, report_type):
        context = request._org_context
        definition = services.definition_for(report_type, context, export=True)
        body = ExportRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        filters = services.parse_filters(body.validated_data["filters"], definition)
        services.build(definition, context, filters)  # validate event / year now, not in the background
        job = services.start_export(
            org_context=context,
            definition=definition,
            filters=filters,
            file_format=body.validated_data["format"],
            request=request,
        )
        return Response(ExportJobSerializer(job).data, status=status.HTTP_202_ACCEPTED)


def _my_job(request, job_id):
    context = request._org_context
    job = ExportJob.objects.for_org(context.organization).filter(pk=job_id, requested_by=request.user).first()
    if job is None:
        raise NotFound()
    return job


class ExportJobView(ReportViewMixin, APIView):
    def get_required_permissions(self):
        return "reports.export"

    @extend_schema(responses=ExportJobSerializer)
    def get(self, request, job_id):
        return Response(ExportJobSerializer(_my_job(request, job_id)).data)


class ExportDownloadView(ReportViewMixin, APIView):
    def get_required_permissions(self):
        return "reports.export"

    @extend_schema(responses={(200, "application/octet-stream"): OpenApiTypes.BINARY})
    def get(self, request, job_id):
        job = _my_job(request, job_id)
        if job.status != ExportJob.Status.DONE:
            raise NotFound()
        response = FileResponse(
            default_storage.open(job.file, "rb"),
            content_type=exporters.CONTENT_TYPES[job.format],
            as_attachment=True,
            filename=job.file_name,
        )
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response
