"""Let an Organization Admin edit or delete a collection (payments/admin_edit.py).

The money triggers from 0002_money_integrity still refuse every delete and every rewrite of amounts, events
and receipts, except inside a transaction that has set `app.admin_override` to 'on' with SET LOCAL. Only
the admin edit service does that, after checking the admin permission, and it writes an audit entry with
the old and new values. A setting made with SET LOCAL ends with the transaction.
"""

from django.db import migrations

OVERRIDE = "coalesce(current_setting('app.admin_override', true), '') = 'on'"

SQL = f"""
CREATE OR REPLACE FUNCTION money_block_delete() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' AND {OVERRIDE} THEN
        RETURN OLD;
    END IF;
    RAISE EXCEPTION '% rows can never be deleted (% blocked)', TG_TABLE_NAME, TG_OP
        USING ERRCODE = 'insufficient_privilege';
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION money_block_rewrite() RETURNS trigger AS $$
BEGIN
    IF {OVERRIDE} THEN
        -- Fields are checked in nested IFs: PL/pgSQL resolves every NEW.x in a condition, even after AND.
        IF TG_TABLE_NAME = 'receipts_receipt' THEN
            IF NEW.receipt_number IS DISTINCT FROM OLD.receipt_number
               OR NEW.sequence IS DISTINCT FROM OLD.sequence
               OR NEW.series_id IS DISTINCT FROM OLD.series_id
               OR NEW.payment_id IS DISTINCT FROM OLD.payment_id THEN
                RAISE EXCEPTION 'receipt numbers never change' USING ERRCODE = 'insufficient_privilege';
            END IF;
        END IF;
        IF NEW.organization_id IS DISTINCT FROM OLD.organization_id THEN
            RAISE EXCEPTION '% organization cannot be changed', TG_TABLE_NAME USING ERRCODE = 'insufficient_privilege';
        END IF;
        RETURN NEW;
    END IF;
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
"""


class Migration(migrations.Migration):
    dependencies = [
        ("receipts", "0005_receipt_corrected_once"),
        ("payments", "0002_collections_anonymous_and_time"),
        ("contributions", "0005_collections_anonymous_and_time"),
    ]
    operations = [migrations.RunSQL(SQL, migrations.RunSQL.noop)]
