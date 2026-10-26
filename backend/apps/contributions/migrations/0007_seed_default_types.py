from django.db import migrations

# Seeding moved to 0008, which runs after the position field exists (seed_types sets it).


class Migration(migrations.Migration):
    dependencies = [
        ("contributions", "0006_balances"),
    ]

    operations = []
