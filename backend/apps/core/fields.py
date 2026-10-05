from rest_framework import serializers


class TenantPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    """A related-object field that only resolves objects inside the request's active organization.

    An id from another organization behaves exactly like a non-existent id.
    """

    def __init__(self, **kwargs):
        self.extra_filter = kwargs.pop("extra_filter", None)
        super().__init__(**kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        request = self.context.get("request")
        context = getattr(request, "_org_context", None) if request else None
        if context is None:
            return queryset.none()
        queryset = queryset.filter(organization=context.organization)
        if self.extra_filter:
            queryset = queryset.filter(**self.extra_filter)
        return queryset
