"""Database-level tenant integrity: child rows cannot reference another organization's parent rows."""

from django.db import migrations

FKS = [
    # (table, constraint, local columns, referenced table, referenced columns)
    ("events_event", "event_fy_same_org", "organization_id, financial_year_id",
     "organizations_financialyear", "organization_id, id"),
    ("events_eventparticipant", "participant_event_same_org", "organization_id, event_id",
     "events_event", "organization_id, id"),
    ("events_eventparticipant", "participant_person_same_org", "organization_id, person_id",
     "people_person", "organization_id, id"),
]

SQL = "\n".join(
    f"ALTER TABLE {t} ADD CONSTRAINT {c} FOREIGN KEY ({cols}) REFERENCES {rt} ({rcols}) DEFERRABLE INITIALLY DEFERRED;"
    for t, c, cols, rt, rcols in FKS
)
REVERSE = "\n".join(f"ALTER TABLE {t} DROP CONSTRAINT IF EXISTS {c};" for t, c, *_ in FKS)


class Migration(migrations.Migration):
    dependencies = [("events", "0001_initial"), ("people", "0001_initial"), ("organizations", "0001_initial")]
    operations = [migrations.RunSQL(SQL, REVERSE)]
