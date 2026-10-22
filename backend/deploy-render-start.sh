#!/bin/sh
# Start command for Dockerfile.render: prepare the database role, migrate, then serve on $PORT.
set -e
if [ -n "$DATABASE_ADMIN_URL" ]; then
  python manage.py ensure_app_role
fi
python manage.py migrate --noinput
# Platform admin for /django-admin/ (the free plan has no shell). Skipped once that email exists.
if [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py createsuperuser --noinput --full_name "${DJANGO_SUPERUSER_FULL_NAME:-Platform Admin}" \
    || echo "Platform admin not created (it may already exist)."
fi
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-10000}" --workers 2 --threads 4 \
  --timeout 120 --access-logfile -
