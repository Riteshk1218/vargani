import django_filters

from apps.core.scoping import scope_money
from apps.core.viewsets import TenantReadOnlyViewSet

from .models import Receipt
from .serializers import ReceiptSerializer


class ReceiptFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name="issued_at", lookup_expr="date__gte")
    date_to = django_filters.DateFilter(field_name="issued_at", lookup_expr="date__lte")

    class Meta:
        model = Receipt
        fields = ["event", "status", "payment"]


class ReceiptViewSet(TenantReadOnlyViewSet):
    """Issued receipts. Receipts are created only by recording a successful payment and never edited."""

    queryset = Receipt.objects.all()
    serializer_class = ReceiptSerializer
    filterset_class = ReceiptFilter
    search_fields = ["receipt_number", "payment__payer__full_name", "payment__payer__mobile"]
    ordering_fields = ["issued_at", "sequence"]
    required_permissions = {"list": "receipts.view", "retrieve": "receipts.view"}

    def get_base_queryset(self):
        return Receipt.objects.for_org(self.organization).select_related("payment__payer")

    def scope_queryset(self, queryset):
        return scope_money(
            queryset,
            self.org_context,
            "receipts.view",
            self.request.user,
            collector="payment__collector",
            person="payment__payer",
        )
