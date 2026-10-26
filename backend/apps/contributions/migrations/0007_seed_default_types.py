from django.db import migrations


def seed_existing(apps, schema_editor):
    from apps.contributions.defaults import seed_types

    Event = apps.get_model("events", "Event")
    ContributionType = apps.get_model("contributions", "ContributionType")
    for event in Event.objects.filter(deleted_at__isnull=True).select_related("organization"):
        seed_types(event, ContributionType)


class Migration(migrations.Migration):
    dependencies = [
        ("contributions", "0006_balances"),
    ]

    operations = [
        migrations.RunPython(seed_existing, migrations.RunPython.noop),
    ]
