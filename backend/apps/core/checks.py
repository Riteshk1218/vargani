from django.core.checks import Warning, register
from django.db import connection


@register("database", deploy=True)
def database_role_is_not_privileged(app_configs, **kwargs):
    """Row-level security does not apply to superusers or roles with BYPASSRLS."""
    if connection.vendor != "postgresql":
        return []
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
            row = cursor.fetchone()
    except Exception:  # noqa: BLE001 - the database may not be reachable during image builds
        return []
    if row and (row[0] or row[1]):
        return [
            Warning(
                "The application connects to PostgreSQL as a superuser or a role with BYPASSRLS, so "
                "row-level security between organizations is not enforced by the database.",
                hint="Connect as an ordinary role (see deploy/db-init.sh).",
                id="core.W001",
            )
        ]
    return []
