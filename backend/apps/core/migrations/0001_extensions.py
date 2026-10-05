from django.contrib.postgres.operations import BtreeGistExtension, CITextExtension, TrigramExtension
from django.db import migrations


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [CITextExtension(), TrigramExtension(), BtreeGistExtension()]
