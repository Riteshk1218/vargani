"""Database URL for hosted Postgres where you only get an owner login (Neon, Supabase and similar).

Set DATABASE_ADMIN_URL to the provider's connection string and leave DATABASE_URL unset. The application then
connects as its own ordinary role (APP_DB_ROLE, default "vargani_app"), whose password is derived from the
secret key, so row-level security applies to it. `manage.py ensure_app_role` creates that role with the owner
login before migrations run.
"""

import hashlib
import hmac
from urllib.parse import quote, urlsplit, urlunsplit

APP_ROLE_DEFAULT = "vargani_app"


def direct_url(url: str) -> str:
    """Neon's pooled host ("-pooler") runs PgBouncer in transaction mode, which drops the per-request
    organization setting that row-level security relies on. Use the direct host instead."""
    parts = urlsplit(url)
    return urlunsplit(parts._replace(netloc=parts.netloc.replace("-pooler.", ".")))


def app_role_password(secret_key: str) -> str:
    return hmac.new(secret_key.encode(), b"vargani-app-db-role", hashlib.sha256).hexdigest()


def app_url(admin_url: str, role: str, secret_key: str) -> str:
    parts = urlsplit(direct_url(admin_url))
    host = parts.netloc.rsplit("@", 1)[-1]
    netloc = f"{quote(role, safe='')}:{app_role_password(secret_key)}@{host}"
    return urlunsplit(parts._replace(netloc=netloc))
