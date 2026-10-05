"""Database-level guarantees for money tables.

1. Composite foreign keys: every row's event, fund, type, person, payment and series belong to the same
   organization (and the same event, where it matters).
2. Money rows can never be deleted or truncated, and amounts / receipt numbers can never be rewritten.
"""

from django.db import migrations

FKS = [
    # (table, constraint, local columns, referenced table, referenced columns)
    ("funds_fund", "fund_event_same_org", "organization_id, event_id", "events_event", "organization_id, id"),
    ("contributions_contributiontype", "ctype_event_same_org", "organization_id, event_id",
     "events_event", "organization_id, id"),
    ("contributions_contributiontype", "ctype_fund_same_event", "event_id, fund_id", "funds_fund", "event_id, id"),
    ("payments_payment", "payment_event_same_org", "organization_id, event_id", "events_event", "organization_id, id"),
    ("payments_payment", "payment_fy_same_org", "organization_id, financial_year_id",
     "organizations_financialyear", "organization_id, id"),
    ("payments_payment", "payment_fy_matches_event", "event_id, financial_year_id",
     "events_event", "id, financial_year_id"),
    ("contributions_contribution", "contribution_fy_matches_event", "event_id, financial_year_id",
     "events_event", "id, financial_year_id"),
    ("receipts_receipt", "receipt_fy_matches_event", "event_id, financial_year_id",
     "events_event", "id, financial_year_id"),
    ("payments_payment", "payment_payer_same_org", "organization_id, payer_id", "people_person", "organization_id, id"),
    ("payments_payment", "payment_collector_same_org", "organization_id, collector_id",
     "organizations_organizationmembership", "organization_id, id"),
    ("contributions_contribution", "contribution_event_same_org", "organization_id, event_id",
     "events_event", "organization_id, id"),
    ("contributions_contribution", "contribution_fy_same_org", "organization_id, financial_year_id",
     "organizations_financialyear", "organization_id, id"),
    ("contributions_contribution", "contribution_type_same_event", "event_id, contribution_type_id",
     "contributions_contributiontype", "event_id, id"),
    ("contributions_contribution", "contribution_fund_same_event", "event_id, fund_id", "funds_fund", "event_id, id"),
    ("contributions_contribution", "contribution_payment_same_event", "event_id, payment_id",
     "payments_payment", "event_id, id"),
    ("contributions_contribution", "contribution_person_same_org", "organization_id, person_id",
     "people_person", "organization_id, id"),
    ("contributions_contribution", "contribution_collector_same_org", "organization_id, collector_id",
     "organizations_organizationmembership", "organization_id, id"),
    ("receipts_receiptseries", "series_event_same_org", "organization_id, event_id",
     "events_event", "organization_id, id"),
    ("receipts_receipt", "receipt_payment_same_event", "event_id, payment_id", "payments_payment", "event_id, id"),
    ("receipts_receipt", "receipt_event_same_org", "organization_id, event_id", "events_event", "organization_id, id"),
    ("receipts_receipt", "receipt_series_same_org", "organization_id, series_id",
     "receipts_receiptseries", "organization_id, id"),
    ("receipts_receipt", "receipt_fy_same_org", "organization_id, financial_year_id",
     "organizations_financialyear", "organization_id, id"),
]

NO_DELETE_TABLES = [
    "payments_payment",
    "contributions_contribution",
    "receipts_receipt",
    "receipts_receiptseries",
]

FK_SQL = "\n".join(
    f"ALTER TABLE {t} ADD CONSTRAINT {c} FOREIGN KEY ({cols}) REFERENCES {rt} ({rcols}) DEFERRABLE INITIALLY DEFERRED;"
    for t, c, cols, rt, rcols in FKS
)
FK_REVERSE = "\n".join(f"ALTER TABLE {t} DROP CONSTRAINT IF EXISTS {c};" for t, c, *_ in FKS)

TRIGGER_SQL = """
CREATE OR REPLACE FUNCTION money_block_delete() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION '% rows can never be deleted (% blocked)', TG_TABLE_NAME, TG_OP
        USING ERRCODE = 'insufficient_privilege';
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION money_block_rewrite() RETURNS trigger AS $$
BEGIN
    IF TG_TABLE_NAME = 'receipts_receipt' THEN
        IF NEW.receipt_number IS DISTINCT FROM OLD.receipt_number
           OR NEW.sequence IS DISTINCT FROM OLD.sequence
           OR NEW.series_id IS DISTINCT FROM OLD.series_id
           OR NEW.payment_id IS DISTINCT FROM OLD.payment_id
           OR NEW.snapshot IS DISTINCT FROM OLD.snapshot
           OR NEW.issued_at IS DISTINCT FROM OLD.issued_at
           OR (OLD.status = 'void' AND NEW.status IS DISTINCT FROM OLD.status) THEN
            RAISE EXCEPTION 'issued receipts are immutable' USING ERRCODE = 'insufficient_privilege';
        END IF;
    ELSIF TG_TABLE_NAME = 'receipts_receiptseries' THEN
        IF NEW.next_number < OLD.next_number OR NEW.prefix IS DISTINCT FROM OLD.prefix
           OR NEW.year_label IS DISTINCT FROM OLD.year_label THEN
            RAISE EXCEPTION 'receipt series can only move forward' USING ERRCODE = 'insufficient_privilege';
        END IF;
    ELSE
        IF NEW.amount IS DISTINCT FROM OLD.amount
           OR NEW.event_id IS DISTINCT FROM OLD.event_id
           OR NEW.organization_id IS DISTINCT FROM OLD.organization_id THEN
            RAISE EXCEPTION '% amount and event cannot be changed', TG_TABLE_NAME
                USING ERRCODE = 'insufficient_privilege';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
""" + "\n".join(
    f"""
CREATE TRIGGER {t}_no_delete BEFORE DELETE ON {t} FOR EACH ROW EXECUTE FUNCTION money_block_delete();
CREATE TRIGGER {t}_no_truncate BEFORE TRUNCATE ON {t} FOR EACH STATEMENT EXECUTE FUNCTION money_block_delete();
CREATE TRIGGER {t}_no_rewrite BEFORE UPDATE ON {t} FOR EACH ROW EXECUTE FUNCTION money_block_rewrite();
"""
    for t in NO_DELETE_TABLES
)

TRIGGER_REVERSE = "\n".join(
    f"DROP TRIGGER IF EXISTS {t}_no_delete ON {t}; DROP TRIGGER IF EXISTS {t}_no_truncate ON {t}; "
    f"DROP TRIGGER IF EXISTS {t}_no_rewrite ON {t};"
    for t in NO_DELETE_TABLES
) + "\nDROP FUNCTION IF EXISTS money_block_delete(); DROP FUNCTION IF EXISTS money_block_rewrite();"


class Migration(migrations.Migration):
    dependencies = [
        ("receipts", "0001_initial"),
        ("contributions", "0001_initial"),
        ("payments", "0001_initial"),
        ("funds", "0001_initial"),
        ("events", "0003_event_id_fy_unique"),
    ]
    operations = [migrations.RunSQL(FK_SQL, FK_REVERSE), migrations.RunSQL(TRIGGER_SQL, TRIGGER_REVERSE)]
