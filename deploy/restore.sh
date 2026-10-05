#!/usr/bin/env bash
# Vargani restore into an EMPTY database. It never overwrites a database that already has tables.
#
#   RESTORE_DATABASE_URL=postgres://user:pass@host:5432/vargani_restore ./deploy/restore.sh /srv/backups/vargani/20261005T020000Z
#   (optional) RESTORE_MEDIA_ROOT=/srv/vargani/media-restore  to unpack uploaded files as well
#
# Typical use: restore into a new database, check it (see DEPLOYMENT.md "Restore drill"), then point
# DATABASE_URL at it. Restoring into the live database is deliberately not supported by this script.
set -euo pipefail

backup="${1:?usage: restore.sh <backup directory>}"
: "${RESTORE_DATABASE_URL:?RESTORE_DATABASE_URL is required (an empty database)}"

(cd "$backup" && sha256sum --check --quiet SHA256SUMS)

tables="$(psql "$RESTORE_DATABASE_URL" -tAc "select count(*) from information_schema.tables where table_schema='public'")"
if [[ "$tables" != "0" ]]; then
  echo "Refusing to restore: the target database already has $tables tables. Use a new, empty database." >&2
  exit 1
fi

echo "[$(date -u +%FT%TZ)] restoring database"
# Tables, data, then indexes/constraints/triggers/policies, in pg_dump's order. One transaction: all or nothing.
# Extension comments can only be set by the extension's owner (a superuser); they are skipped.
toc="$(mktemp)"
trap 'rm -f "$toc"' EXIT
pg_restore --list "$backup/database.dump" | grep -v 'COMMENT - EXTENSION' > "$toc"
pg_restore --dbname="$RESTORE_DATABASE_URL" --no-owner --no-privileges --single-transaction --exit-on-error \
  --use-list="$toc" "$backup/database.dump"

if [[ -n "${RESTORE_MEDIA_ROOT:-}" && -f "$backup/media.tar.gz" ]]; then
  mkdir -p "$RESTORE_MEDIA_ROOT"
  tar -C "$RESTORE_MEDIA_ROOT" -xzf "$backup/media.tar.gz"
fi

psql "$RESTORE_DATABASE_URL" -tAc "select 'organizations: ' || count(*) from organizations_organization
  union all select 'payments: ' || count(*) from payments_payment
  union all select 'receipts: ' || count(*) from receipts_receipt
  union all select 'audit entries: ' || count(*) from audit_auditlog"
echo "[$(date -u +%FT%TZ)] restore complete"
