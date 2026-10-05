#!/usr/bin/env bash
# Vargani backup: database (custom-format pg_dump) + uploaded files (logos, bills, exports).
#
#   DATABASE_URL=postgres://user:pass@host:5432/vargani MEDIA_ROOT=/srv/vargani/media \
#   BACKUP_DIR=/srv/backups KEEP_DAYS=30 ./deploy/backup.sh
#
# Optional: BACKUP_S3_URI=s3://bucket/vargani (needs the aws CLI) copies each backup off the server.
# Run it from cron every night; test a restore (restore.sh) at least once a month.
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL is required}"
BACKUP_DIR="${BACKUP_DIR:-/srv/backups/vargani}"
KEEP_DAYS="${KEEP_DAYS:-30}"
MEDIA_ROOT="${MEDIA_ROOT:-}"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
target="$BACKUP_DIR/$stamp"
mkdir -p "$target"
umask 077

echo "[$(date -u +%FT%TZ)] dumping database"
# --enable-row-security: the application user is subject to row-level security; with no organization
# selected the policies allow every row, so the dump is complete without needing a superuser.
pg_dump --dbname="$DATABASE_URL" --format=custom --compress=9 --no-owner --no-privileges \
  --enable-row-security --file="$target/database.dump"
pg_restore --list "$target/database.dump" > /dev/null  # fails if the file is unreadable

if [[ -n "$MEDIA_ROOT" && -d "$MEDIA_ROOT" ]]; then
  echo "[$(date -u +%FT%TZ)] archiving uploaded files"
  tar -C "$MEDIA_ROOT" -czf "$target/media.tar.gz" .
fi

(cd "$target" && sha256sum ./* > SHA256SUMS)
echo "$stamp" > "$BACKUP_DIR/LATEST"

if [[ -n "${BACKUP_S3_URI:-}" ]]; then
  echo "[$(date -u +%FT%TZ)] copying to $BACKUP_S3_URI/$stamp"
  aws s3 cp --recursive --only-show-errors "$target" "$BACKUP_S3_URI/$stamp"
fi

# Keep the last KEEP_DAYS days locally (off-site copies follow the bucket's own lifecycle rules).
find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -name '20*' -mtime +"$KEEP_DAYS" -exec rm -rf {} +

echo "[$(date -u +%FT%TZ)] backup complete: $target ($(du -sh "$target" | cut -f1))"
