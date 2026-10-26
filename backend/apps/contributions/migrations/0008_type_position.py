from django.db import migrations, models


def seed_existing(apps, schema_editor):
    from apps.contributions.defaults import seed_types

    Event = apps.get_model("events", "Event")
    ContributionType = apps.get_model("contributions", "ContributionType")
    for event in Event.objects.filter(deleted_at__isnull=True).select_related("organization"):
        seed_types(event, ContributionType)


class Migration(migrations.Migration):
    dependencies = [
        ("contributions", "0007_seed_default_types"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="contributiontype",
            options={"ordering": ["position", "name"]},
        ),
        migrations.AddField(
            model_name="contributiontype",
            name="position",
            field=models.PositiveSmallIntegerField(default=100),
        ),
        migrations.RunPython(seed_existing, migrations.RunPython.noop),
    ]
