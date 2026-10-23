"""PostgreSQL row-level security: a database-level guard behind the application's tenant filters.

Every request that works inside an organization sets the session variable `app.org_id`. Policies on every
tenant table then hide (and refuse to write) rows of any other organization, even if a query in the code
forgot its `organization` filter. Work outside an organization (login, the cross-organization notification
list, payment webhooks, Celery jobs) runs with the variable empty and relies on the application filters.

New tenant tables must be added to TENANT_TABLES and get a migration that calls `enable_sql`;
`test_every_tenant_table_has_row_level_security` fails until they do.
"""

from contextlib import contextmanager

from django.db import connection

GUC = "app.org_id"

TENANT_TABLES = [
    "audit_auditlog",
    "contributions_collectorassignment",
    "contributions_contribution",
    "contributions_contributiontype",
    "events_event",
    "events_eventparticipant",
    "expenses_expense",
    "expenses_expenseattachment",
    "expenses_expensecategory",
    "expenses_otherincome",
    "funds_fund",
    "gateway_gatewayconfig",
    "gateway_gatewayevent",
    "notifications_notification",
    "organizations_financialyear",
    "organizations_invitation",
    "organizations_organizationmembership",
    "organizations_role",
    "payments_payment",
    "people_person",
    "receipts_receipt",
    "receipts_receiptseries",
    "receipts_receiptshare",
    "receipts_receiptvoidrequest",
    "reports_exportjob",
]

POLICY = "tenant_isolation"
_CONDITION = (
    f"coalesce(current_setting('{GUC}', true), '') = '' "
    "OR organization_id IS NULL "
    f"OR organization_id = nullif(current_setting('{GUC}', true), '')::uuid"
)


def enable_sql(table: str) -> str:
    return (
        f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY; "
        f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY; "
        f"DROP POLICY IF EXISTS {POLICY} ON {table}; "
        f"CREATE POLICY {POLICY} ON {table} USING ({_CONDITION}) WITH CHECK ({_CONDITION});"
    )


def disable_sql(table: str) -> str:
    return (
        f"DROP POLICY IF EXISTS {POLICY} ON {table}; "
        f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY; "
        f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;"
    )


def _set(value: str) -> None:
    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config(%s, %s, false)", [GUC, value])


def activate(organization_id) -> None:
    _set(str(organization_id))


def deactivate() -> None:
    _set("")


def _current() -> str:
    if connection.vendor != "postgresql":
        return ""
    with connection.cursor() as cursor:
        cursor.execute("SELECT coalesce(current_setting(%s, true), '')", [GUC])
        return cursor.fetchone()[0]


@contextmanager
def unscoped():
    """Look across organizations for one check that must see every row (e.g. whether a login is also used
    by another organization), then restore the request's organization."""
    previous = _current()
    deactivate()
    try:
        yield
    finally:
        _set(previous)


class TenantDatabaseMiddleware:
    """Clears `app.org_id` after every request so a reused database connection never carries it over."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        finally:
            if getattr(request, "_rls_org", None) is not None:
                deactivate()
