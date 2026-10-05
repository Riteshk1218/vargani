from apps.core.viewsets import TenantModelViewSet

from .models import Fund
from .serializers import FundSerializer


class FundViewSet(TenantModelViewSet):
    """Funds of an event. Archive with PATCH {"is_active": false}; funds are never deleted."""

    queryset = Fund.objects.all()
    serializer_class = FundSerializer
    filterset_fields = ["event", "is_active"]
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]
    required_permissions = {
        "list": "funds.view",
        "retrieve": "funds.view",
        "create": "funds.manage",
        "partial_update": "funds.manage",
    }
