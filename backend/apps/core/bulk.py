"""Delete many rows of a list at once (Organization Admin).

A list endpoint mixes in BulkDeleteMixin and says how one row is deleted (`bulk_delete_one`), using the same
service as its single delete, so each row is soft-deleted or voided and audited exactly as it would be alone.
POST <list>/bulk-delete/ {"ids": [...]} answers {"deleted": n, "failed": [{"id", "message"}]}: a row that cannot
be deleted (already deleted, your own access, ...) is reported and the others still go.
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils.translation import gettext as _
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.response import Response

BULK_DELETE_LIMIT = 500


class BulkDeleteSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False, max_length=BULK_DELETE_LIMIT)


def _message(exc) -> str:
    detail = getattr(exc, "detail", None) or getattr(exc, "messages", None) or exc
    while isinstance(detail, (list, dict)) and detail:
        detail = next(iter(detail.values())) if isinstance(detail, dict) else detail[0]
    return str(detail)


class BulkDeleteMixin:
    """Adds POST bulk-delete/. Map "bulk_delete" in `required_permissions` and implement `bulk_delete_one`."""

    def bulk_delete_one(self, obj) -> None:
        raise NotImplementedError

    def bulk_delete_targets(self, rows):
        """The records to delete for the chosen rows (e.g. a contribution line deletes its whole collection)."""
        return rows

    @extend_schema(
        request=BulkDeleteSerializer,
        responses=inline_serializer(
            "BulkDeleteResult",
            {
                "deleted": serializers.IntegerField(),
                "failed": serializers.ListField(child=serializers.DictField()),
            },
        ),
    )
    @action(detail=False, methods=["post"], url_path="bulk-delete")
    def bulk_delete(self, request):
        body = BulkDeleteSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        ids = set(body.validated_data["ids"])
        rows = list(self.get_queryset().filter(pk__in=ids))
        found = {row.pk for row in rows}
        failed = [{"id": str(pk), "message": _("Not found.")} for pk in ids - found]
        deleted = 0
        for target in self.bulk_delete_targets(rows):
            try:
                with transaction.atomic():
                    self.bulk_delete_one(target)
                deleted += 1
            except (APIException, DjangoValidationError) as exc:
                failed.append({"id": str(target.pk), "message": _message(exc)})
        return Response({"deleted": deleted, "failed": failed})
