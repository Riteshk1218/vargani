"""Let an Organization Admin edit any expense or other income (see receipts/0006_admin_override).

Outside a transaction with `app.admin_override` = 'on', the rules from 0002_integrity still apply.
"""

from django.db import migrations

SQL = """
CREATE OR REPLACE FUNCTION spending_block_rewrite() RETURNS trigger AS $$
BEGIN
    IF NEW.organization_id IS DISTINCT FROM OLD.organization_id OR NEW.event_id IS DISTINCT FROM OLD.event_id THEN
        RAISE EXCEPTION '% organization and event cannot be changed', TG_TABLE_NAME
            USING ERRCODE = 'insufficient_privilege';
    END IF;
    IF coalesce(current_setting('app.admin_override', true), '') = 'on' THEN
        RETURN NEW;
    END IF;
    IF OLD.status = 'void' AND NEW.status IS DISTINCT FROM OLD.status THEN
        RAISE EXCEPTION '% void rows are final', TG_TABLE_NAME USING ERRCODE = 'insufficient_privilege';
    END IF;
    IF TG_TABLE_NAME = 'expenses_expense' THEN
        IF OLD.status = 'approved' AND (
               NEW.status NOT IN ('approved', 'void')
               OR NEW.amount IS DISTINCT FROM OLD.amount
               OR NEW.category_id IS DISTINCT FROM OLD.category_id
               OR NEW.expense_date IS DISTINCT FROM OLD.expense_date) THEN
            RAISE EXCEPTION 'approved expenses cannot be changed, only voided'
                USING ERRCODE = 'insufficient_privilege';
        END IF;
        IF OLD.status = 'void' AND NEW.amount IS DISTINCT FROM OLD.amount THEN
            RAISE EXCEPTION 'void expenses cannot be changed' USING ERRCODE = 'insufficient_privilege';
        END IF;
    ELSIF NEW.amount IS DISTINCT FROM OLD.amount THEN
        RAISE EXCEPTION 'other income amount cannot be changed' USING ERRCODE = 'insufficient_privilege';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""


class Migration(migrations.Migration):
    dependencies = [("expenses", "0003_collections_anonymous_and_time"), ("receipts", "0006_admin_override")]
    operations = [migrations.RunSQL(SQL, migrations.RunSQL.noop)]
