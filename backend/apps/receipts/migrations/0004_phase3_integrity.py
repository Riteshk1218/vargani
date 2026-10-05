"""Composite tenant keys for Phase 3 tables (see 0002_money_integrity)."""

from django.db import migrations

FKS = [
    ("contributions_collectorassignment", "assignment_event_same_org", "organization_id, event_id",
     "events_event", "organization_id, id"),
    ("contributions_collectorassignment", "assignment_collector_same_org", "organization_id, collector_id",
     "organizations_organizationmembership", "organization_id, id"),
    ("contributions_collectorassignment", "assignment_person_same_org", "organization_id, person_id",
     "people_person", "organization_id, id"),
    ("receipts_receiptshare", "share_receipt_same_org", "organization_id, receipt_id",
     "receipts_receipt", "organization_id, id"),
    ("receipts_receiptvoidrequest", "void_request_receipt_same_org", "organization_id, receipt_id",
     "receipts_receipt", "organization_id, id"),
]

SQL = "\n".join(
    f"ALTER TABLE {t} ADD CONSTRAINT {c} FOREIGN KEY ({cols}) REFERENCES {rt} ({rcols}) DEFERRABLE INITIALLY DEFERRED;"
    for t, c, cols, rt, rcols in FKS
) + """
CREATE TRIGGER receipts_receiptvoidrequest_no_delete BEFORE DELETE ON receipts_receiptvoidrequest
    FOR EACH ROW EXECUTE FUNCTION money_block_delete();
CREATE TRIGGER receipts_receiptvoidrequest_no_truncate BEFORE TRUNCATE ON receipts_receiptvoidrequest
    FOR EACH STATEMENT EXECUTE FUNCTION money_block_delete();
"""
REVERSE = "\n".join(f"ALTER TABLE {t} DROP CONSTRAINT IF EXISTS {c};" for t, c, *_ in FKS) + """
DROP TRIGGER IF EXISTS receipts_receiptvoidrequest_no_delete ON receipts_receiptvoidrequest;
DROP TRIGGER IF EXISTS receipts_receiptvoidrequest_no_truncate ON receipts_receiptvoidrequest;
"""


class Migration(migrations.Migration):
    dependencies = [("receipts", "0003_phase3"), ("contributions", "0004_phase3")]
    operations = [migrations.RunSQL(SQL, REVERSE)]
