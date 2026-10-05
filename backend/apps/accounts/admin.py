from django.contrib import admin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["full_name", "email", "mobile", "is_active", "is_platform_admin", "date_joined"]
    search_fields = ["full_name", "email", "mobile"]
    readonly_fields = ["password", "last_login", "date_joined"]
