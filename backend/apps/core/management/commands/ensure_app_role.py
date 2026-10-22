"""Create or update the application's ordinary database role on hosted Postgres (see config/dburl.py).

Runs with DATABASE_ADMIN_URL (the provider's owner login), before migrations. Safe to run on every start.
"""

from urllib.parse import unquote, urlsplit

import psycopg
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from psycopg import sql

from config import dburl

EXTENSIONS = ("citext", "pg_trgm", "btree_gist")  # created by the owner; core/0001 then finds them


class Command(BaseCommand):
    help = "Create the application's database role (no superuser, no BYPASSRLS) using DATABASE_ADMIN_URL."

    def handle(self, *args, **options):
        admin_url = settings.DATABASE_ADMIN_URL
        if not admin_url:
            raise CommandError("DATABASE_ADMIN_URL is not set.")
        role = settings.APP_DB_ROLE
        database = unquote(urlsplit(admin_url).path.lstrip("/")) or "postgres"
        password = dburl.app_role_password(settings.SECRET_KEY)
        with psycopg.connect(dburl.direct_url(admin_url), autocommit=True) as conn:
            exists = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", [role]).fetchone()
            verb = "ALTER" if exists else "CREATE"
            conn.execute(
                sql.SQL(verb + " ROLE {} WITH LOGIN PASSWORD {}").format(sql.Identifier(role), sql.Literal(password))
            )
            for extension in EXTENSIONS:
                conn.execute(sql.SQL("CREATE EXTENSION IF NOT EXISTS {}").format(sql.Identifier(extension)))
            conn.execute(
                sql.SQL("GRANT CONNECT, CREATE, TEMPORARY ON DATABASE {} TO {}").format(
                    sql.Identifier(database), sql.Identifier(role)
                )
            )
            conn.execute(sql.SQL("GRANT USAGE, CREATE ON SCHEMA public TO {}").format(sql.Identifier(role)))
            flags = conn.execute("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = %s", [role]).fetchone()
        if any(flags):
            raise CommandError(f"Role {role} is a superuser or has BYPASSRLS; row-level security would not apply.")
        self.stdout.write(f"Database role {role} is ready ({'updated' if exists else 'created'}).")
