from django.contrib import admin

from .models import Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    """Platform operations only: no financial data is exposed here."""

    list_display = ["name", "status", "city", "created_at"]
    list_filter = ["status"]
    search_fields = ["name", "slug"]
    fields = ["name", "slug", "status", "city", "state", "created_at"]
    readonly_fields = ["name", "slug", "city", "state", "created_at"]
