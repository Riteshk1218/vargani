#!/usr/bin/env bash
# Runs once, when the database volume is first created (docker-entrypoint-initdb.d).
# The application connects as an ordinary role, NOT a superuser: superusers skip row-level security, and the
# app should not be able to switch off the money and audit protections either.
set -euo pipefail
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres \
  --set app_user="$APP_DB_USER" --set app_password="$APP_DB_PASSWORD" --set app_db="$APP_DB_NAME" <<'SQL'
CREATE ROLE :"app_user" LOGIN PASSWORD :'app_password' NOSUPERUSER NOCREATEROLE NOBYPASSRLS CREATEDB;
CREATE DATABASE :"app_db" OWNER :"app_user";
SQL
