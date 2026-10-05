"""Member portal: a member sees only their own record, contributions, payments and receipts.

Every query starts from the Person linked to request.user in the active organization. No endpoint accepts a
person id, so guessing another member's receipt or payment id answers 404.
"""

from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import APIException, NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.contributions.models import Contribution, ContributionType
from apps.contributions.selectors import expected_per_person
from apps.core.permissions import HasOrgPermission
from apps.events.models import Event
from apps.payments.models import Payment
from apps.payments.serializers import PaymentSerializer
from apps.people.models import Person
from apps.receipts.models import Receipt
from apps.receipts.serializers import ReceiptSerializer
from apps.receipts.views import pdf_response

from .linking import portal_enabled


class PortalUnavailable(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = "portal_unavailable"
    default_detail = _("The member portal is not available for this organization.")


class NotLinked(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = "portal_not_linked"
    default_detail = _("Your login is not linked to a member record yet. Please contact your organization.")


def _money(value) -> str:
    return f"{(value or Decimal(0)):.2f}"


class PortalMixin:
    permission_classes = [IsAuthenticated, HasOrgPermission]
    pagination_class = None

    def get_organization_id(self):
        return None

    def get_required_permissions(self):
        return "portal.self"

    @property
    def org(self):
        return self.request._org_context.organization

    def person(self) -> Person:
        if not portal_enabled(self.org):
            raise PortalUnavailable()
        person = Person.objects.for_org(self.org).alive().filter(user=self.request.user).first()
        if person is None:
            raise NotLinked()
        return person

    def event_filter(self):
        event_id = self.request.query_params.get("event")
        if not event_id:
            return None
        event = Event.objects.for_org(self.org).alive().filter(pk=event_id).first()
        if event is None:
            raise NotFound()
        return event


class PortalMeView(PortalMixin, APIView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        person = self.person()
        events = (
            Event.objects.for_org(self.org)
            .alive()
            .filter(Q(participants__person=person) | Q(contributions__person=person))
            .distinct()
            .order_by("-start_date", "name")
        )
        return Response(
            {
                "person": {
                    "id": str(person.pk),
                    "full_name": person.full_name,
                    "mobile": person.mobile,
                    "email": person.email,
                    "address": ", ".join(p for p in [person.unit, person.building, person.area, person.city] if p),
                },
                "organization": {"id": str(self.org.pk), "name": self.org.name, "currency": self.org.currency},
                "events": [{"id": str(e.pk), "name": e.name, "status": e.status} for e in events],
                "online_payments": _online_enabled(self.org),
            }
        )


def _online_enabled(org) -> bool:
    from apps.gateway.models import GatewayConfig

    return GatewayConfig.objects.filter(organization=org, is_active=True).exists()


class PortalSummaryView(PortalMixin, APIView):
    """My totals: paid per event and contribution type, and what is still due on mandatory types."""

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        person = self.person()
        event = self.event_filter()
        lines = Contribution.objects.for_org(self.org).filter(person=person, status=Contribution.Status.CONFIRMED)
        if event is not None:
            lines = lines.filter(event=event)
        total = lines.aggregate(total=Sum("amount"), payments=Count("payment", distinct=True))
        by_event = lines.values("event", "event__name").annotate(total=Sum("amount")).order_by("event__name")
        by_type = (
            lines.values("contribution_type", "contribution_type__name", "event__name")
            .annotate(total=Sum("amount"))
            .order_by("event__name", "contribution_type__name")
        )
        types = ContributionType.objects.for_org(self.org).filter(
            is_mandatory=True, is_active=True, event__participants__person=person
        )
        if event is not None:
            types = types.filter(event=event)
        today = timezone.localdate()
        dues = []
        for ctype in types.select_related("event").distinct():
            expected = expected_per_person(ctype, today)
            paid = lines.filter(contribution_type=ctype).aggregate(total=Sum("amount"))["total"] or Decimal(0)
            due = max(expected - paid, Decimal(0))
            dues.append(
                {
                    "contribution_type": str(ctype.pk),
                    "name": ctype.name,
                    "event": ctype.event.name,
                    "expected": _money(expected),
                    "paid": _money(paid),
                    "due": _money(due),
                }
            )
        return Response(
            {
                "total_paid": _money(total["total"]),
                "payments": total["payments"],
                "by_event": [
                    {"id": str(r["event"]), "name": r["event__name"], "total": _money(r["total"])} for r in by_event
                ],
                "by_type": [
                    {
                        "id": str(r["contribution_type"]),
                        "name": r["contribution_type__name"],
                        "event": r["event__name"],
                        "total": _money(r["total"]),
                    }
                    for r in by_type
                ],
                "dues": dues,
                "total_due": _money(sum((Decimal(d["due"]) for d in dues), Decimal(0))),
            }
        )


class PortalPaymentsView(PortalMixin, generics.ListAPIView):
    serializer_class = PaymentSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Payment.objects.none()
        qs = (
            Payment.objects.for_org(self.org)
            .filter(payer=self.person())
            .exclude(status=Payment.Status.PENDING, mode="online")  # abandoned checkouts are not shown
            .select_related("event", "payer", "collector__user")
            .prefetch_related("lines__contribution_type", "lines__fund", "receipts")
            .order_by("-paid_at")
        )
        event = self.event_filter()
        return qs.filter(event=event) if event else qs


class PortalReceiptsView(PortalMixin, generics.ListAPIView):
    serializer_class = ReceiptSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Receipt.objects.none()
        qs = (
            Receipt.objects.for_org(self.org)
            .filter(payment__payer=self.person())
            .select_related("payment__payer", "event")
            .order_by("-issued_at")
        )
        event = self.event_filter()
        return qs.filter(event=event) if event else qs


class PortalReceiptDetailView(PortalMixin, APIView):
    def _receipt(self, pk):
        return get_object_or_404(
            Receipt.objects.for_org(self.org).filter(payment__payer=self.person()).select_related("payment__payer"),
            pk=pk,
        )

    @extend_schema(responses=ReceiptSerializer)
    def get(self, request, pk):
        return Response(ReceiptSerializer(self._receipt(pk), context={"request": request}).data)


class PortalReceiptPdfView(PortalReceiptDetailView):
    @extend_schema(responses={(200, "application/pdf"): OpenApiTypes.BINARY})
    def get(self, request, pk):
        return pdf_response(self._receipt(pk), inline=request.query_params.get("inline") == "1")
