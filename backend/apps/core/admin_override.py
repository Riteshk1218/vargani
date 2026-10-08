"""Admin edit and delete of money records.

The database refuses to delete money rows or rewrite amounts (receipts/0002_money_integrity). An Organization
Admin may still edit or delete any record: the service checks `records.admin_edit`, then calls
`allow_admin_changes()` inside its transaction, which lifts those triggers for that transaction only
(SET LOCAL ends with it). Every such change is written to the audit log with the old and new values.
"""

from django.db import connection, transaction

ADMIN_EDIT = "records.admin_edit"
ADMIN_EDIT_ACTION = "admin_edit"
ADMIN_DELETE_ACTION = "admin_delete"


def allow_admin_changes() -> None:
    assert transaction.get_connection().in_atomic_block, "allow_admin_changes must run inside a transaction"
    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL app.admin_override = 'on'")
