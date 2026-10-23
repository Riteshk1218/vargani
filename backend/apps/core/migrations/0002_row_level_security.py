from django.db import migrations

from apps.core.rls import disable_sql, enable_sql

# Frozen: tables added later enable row-level security in their own migration.
TABLES = [
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


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_extensions"),
        ("audit", "0002_append_only"),
        ("contributions", "0004_phase3"),
        ("events", "0003_event_id_fy_unique"),
        ("expenses", "0002_integrity"),
        ("funds", "0001_initial"),
        ("gateway", "0001_initial"),
        ("notifications", "0002_devicetoken"),
        ("organizations", "0001_initial"),
        ("payments", "0001_initial"),
        ("people", "0001_initial"),
        ("receipts", "0005_receipt_corrected_once"),
        ("reports", "0001_initial"),
    ]

    operations = [migrations.RunSQL(sql=enable_sql(table), reverse_sql=disable_sql(table)) for table in TABLES]
