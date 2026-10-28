from django.db import migrations


# The built-in "Monthly Contribution" type, in English, Marathi and Hindi. It is no longer added to new events.
SEEDED_MONTHLY = ["Monthly Contribution", "मासिक वर्गणी", "मासिक योगदान"]


def hide_monthly(apps, schema_editor):
    """The built-in "Monthly Contribution" type leaves every dropdown. It is archived, not deleted: past collections
    keep showing it, and an admin can restore it in the event's setup. Monthly types an organization made itself
    (e.g. "Monthly") stay as they are."""
    ContributionType = apps.get_model("contributions", "ContributionType")
    ContributionType.objects.filter(kind="recurring_monthly", name__in=SEEDED_MONTHLY, is_active=True).update(
        is_active=False
    )


class Migration(migrations.Migration):
    dependencies = [
        ("contributions", "0008_type_position"),
    ]

    operations = [
        migrations.RunPython(hide_monthly, migrations.RunPython.noop),
    ]
