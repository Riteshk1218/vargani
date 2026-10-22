#!/bin/sh
# Start command for Dockerfile.render: prepare the database role, migrate, then serve on $PORT.
set -e
if [ -n "$DATABASE_ADMIN_URL" ]; then
  python manage.py ensure_app_role
fi
python manage.py migrate --noinput
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-10000}" --workers 2 --threads 4 \
  --timeout 120 --access-logfile -
