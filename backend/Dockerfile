FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DJANGO_SETTINGS_MODULE=config.settings.prod
RUN apt-get update && apt-get install -y --no-install-recommends gettext libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libharfbuzz-subset0 fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home app
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
ARG BUILD_ENV="DJANGO_SECRET_KEY=build FIELD_ENCRYPTION_KEY=build ALLOW_CONSOLE_SMS=true DATABASE_URL=sqlite:////tmp/build.db"
RUN env $BUILD_ENV python manage.py compilemessages \
    && env $BUILD_ENV python manage.py collectstatic --noinput
RUN mkdir -p /srv/media && chown -R app /srv/media /app/staticfiles
USER app
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
