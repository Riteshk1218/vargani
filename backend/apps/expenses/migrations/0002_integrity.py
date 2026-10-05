"""Database guarantees for expenses and other income, plus default categories for existing organizations.

- Composite foreign keys keep event, financial year, category, fund and bills inside one organization/event.
- Expenses and other income can never be deleted. Once an expense is approved its amount, event, category and
  date are fixed and it can only become void; a void row never changes status again. Other income amounts never
  change and void is final.
"""

from django.db import migrations

FKS = [
    ("expenses_expense", "expense_event_same_org", "organization_id, event_id", "events_event", "organization_id, id"),
    ("expenses_expense", "expense_fy_matches_event", "event_id, financial_year_id",
     "events_event", "id, financial_year_id"),
    ("expenses_expense", "expense_category_same_org", "organization_id, category_id",
     "expenses_expensecategory", "organization_id, id"),
    ("expenses_expenseattachment", "attachment_expense_same_org", "organization_id, expense_id",
     "expenses_expense", "organization_id, id"),
    ("expenses_otherincome", "income_event_same_org", "organization_id, event_id",
     "events_event", "organization_id, id"),
    ("expenses_otherincome", "income_fy_matches_event", "event_id, financial_year_id",
     "events_event", "id, financial_year_id"),
    ("expenses_otherincome", "income_fund_same_event", "event_id, fund_id", "funds_fund", "event_id, id"),
]
TABLES = ["expenses_expense", "expenses_otherincome"]

FK_SQL = "\n".join(
    f"ALTER TABLE {t} ADD CONSTRAINT {c} FOREIGN KEY ({cols}) REFERENCES {rt} ({rcols}) DEFERRABLE INITIALLY DEFERRED;"
    for t, c, cols, rt, rcols in FKS
)
FK_REVERSE = "\n".join(f"ALTER TABLE {t} DROP CONSTRAINT IF EXISTS {c};" for t, c, *_ in FKS)

TRIGGER_SQL = """
CREATE OR REPLACE FUNCTION spending_block_rewrite() RETURNS trigger AS $$
BEGIN
    IF NEW.organization_id IS DISTINCT FROM OLD.organization_id OR NEW.event_id IS DISTINCT FROM OLD.event_id THEN
        RAISE EXCEPTION '% organization and event cannot be changed', TG_TABLE_NAME
            USING ERRCODE = 'insufficient_privilege';
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
""" + "\n".join(
    f"""
CREATE TRIGGER {t}_no_delete BEFORE DELETE ON {t} FOR EACH ROW EXECUTE FUNCTION money_block_delete();
CREATE TRIGGER {t}_no_truncate BEFORE TRUNCATE ON {t} FOR EACH STATEMENT EXECUTE FUNCTION money_block_delete();
CREATE TRIGGER {t}_no_rewrite BEFORE UPDATE ON {t} FOR EACH ROW EXECUTE FUNCTION spending_block_rewrite();
"""
    for t in TABLES
)
TRIGGER_REVERSE = "\n".join(
    f"DROP TRIGGER IF EXISTS {t}_no_delete ON {t}; DROP TRIGGER IF EXISTS {t}_no_truncate ON {t}; "
    f"DROP TRIGGER IF EXISTS {t}_no_rewrite ON {t};"
    for t in TABLES
) + "\nDROP FUNCTION IF EXISTS spending_block_rewrite();"


def seed_existing(apps, schema_editor):
    from apps.expenses.defaults import seed_categories

    Organization = apps.get_model("organizations", "Organization")
    ExpenseCategory = apps.get_model("expenses", "ExpenseCategory")
    for org in Organization.objects.all():
        seed_categories(org, ExpenseCategory)


class Migration(migrations.Migration):
    dependencies = [
        ("expenses", "0001_initial"),
        ("receipts", "0002_money_integrity"),  # money_block_delete()
        ("funds", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(FK_SQL, FK_REVERSE),
        migrations.RunSQL(TRIGGER_SQL, TRIGGER_REVERSE),
        migrations.RunPython(seed_existing, migrations.RunPython.noop),
    ]
