from django.apps import AppConfig
from django.db.models.signals import post_migrate


class OrganizationsConfig(AppConfig):
    name = "apps.organizations"
    label = "organizations"

    def ready(self):
        from .catalog import sync_catalog

        post_migrate.connect(sync_catalog, sender=self)
