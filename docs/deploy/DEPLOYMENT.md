# Deploying Vargani

This guide puts Vargani on one Linux server with Docker: the website, the API, background jobs, the database
and automatic HTTPS. One small server handles many organizations; scale up later without changing code.

Nothing in this repository deploys by itself. Every step below is run by you (or your developer) on your
server.

---

## 1. What you need

| Item | Notes |
|---|---|
| A server | Ubuntu 24.04, 2 vCPU, 4 GB RAM, 40 GB SSD is plenty to start (e.g. a Mumbai-region VM) |
| A domain | e.g. `vargani.yourtrust.in`, with an **A record** pointing to the server's IP |
| SMS provider | MSG91 account with a **DLT-registered** OTP template (required for login codes in India) |
| Email (SMTP) | for invitations and password resets: Amazon SES, Zoho, Gmail Workspace, etc. |
| Razorpay (optional) | each organization adds its own keys in Settings → Online payments |
| Firebase (optional) | for push notifications to the mobile app |
| Off-site storage (recommended) | an S3-compatible bucket for nightly backups |

Install Docker on the server: `curl -fsSL https://get.docker.com | sh`.

---

## 2. First deployment

```bash
git clone <your repository> /srv/vargani && cd /srv/vargani
cp deploy/.env.example deploy/.env
nano deploy/.env            # fill in every empty value (see section 3)
docker compose -f docker-compose.prod.yml --env-file deploy/.env up -d --build
docker compose -f docker-compose.prod.yml --env-file deploy/.env logs -f migrate api
```

When the `migrate` service has finished and `api` is healthy, open `https://<your domain>`.
Caddy obtains the HTTPS certificate automatically on first visit (ports 80 and 443 must be open).

Create the first account from the website's **Register** page, then create the organization. Optionally
create a Django superuser for the `/django-admin/` screen:

```bash
docker compose -f docker-compose.prod.yml --env-file deploy/.env exec api python manage.py createsuperuser
```

---

## 3. Settings (`deploy/.env`)

| Setting | What to put |
|---|---|
| `DOMAIN`, `DJANGO_ALLOWED_HOSTS` | your domain, e.g. `vargani.yourtrust.in` |
| `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `FRONTEND_URL`, `API_PUBLIC_URL` | `https://` + your domain |
| `DJANGO_SECRET_KEY`, `JWT_SIGNING_KEY` | two different long random strings |
| `FIELD_ENCRYPTION_KEY` | a Fernet key; encrypts Razorpay secrets. **Back it up separately**: without it, saved gateway secrets cannot be read and must be entered again |
| `POSTGRES_PASSWORD` | password of the application's database login (an ordinary role) |
| `POSTGRES_ADMIN_PASSWORD` | password of the database administrator (`postgres`), for maintenance only |
| `SMS_BACKEND`, `SMS_MSG91_AUTH_KEY`, `SMS_MSG91_TEMPLATE_ID` | MSG91 details (template variables `otp` and `minutes`) |
| `EMAIL_*`, `DEFAULT_FROM_EMAIL` | SMTP details |
| `STORAGE_*` | leave `local` (files on a Docker volume) or use S3-compatible storage |
| `PUSH_BACKEND`, `FCM_SERVICE_ACCOUNT_FILE` | `fcm` and the service-account file path once the mobile app is ready |
| `SENTRY_DSN` | optional error tracking (add `sentry-sdk` to `backend/requirements.txt` first) |

The API refuses to start in production if `FIELD_ENCRYPTION_KEY` is missing or if SMS is still the console
backend (members would never receive their login codes).

---

## 4. What runs where

```
Internet ─► caddy (HTTPS, :443) ─► web (nginx: website + /api proxy) ─► api (Django + gunicorn)
                                                                       ├─► db (PostgreSQL 16)
                                                                       └─► redis ◄─ worker (Celery) / beat (schedules)
```

- **worker** sends SMS, emails and push notifications and builds report exports.
- **beat** runs the monthly dues reminders (5th of each month, 10:00 IST) for organizations that switched
  them on.
- **migrate** runs database migrations on every start and exits.
- Uploaded files live on the `media` volume. Only organization logos are publicly reachable; bills and
  exports are served by the API after a permission check.

### Security built in

- Every table that holds organization data has PostgreSQL **row-level security**. Each API request that works
  inside an organization tells the database which organization it is, and the database hides and refuses
  rows of every other organization, even if application code had a bug.
- The application connects to the database as an ordinary role created by `deploy/db-init.sh`, never as the
  administrator, because administrators skip row-level security. `python manage.py check --deploy` warns
  (`core.W001`) if this is ever misconfigured.
- Money records (payments, contributions, receipts, expenses, other income) and the audit log cannot be
  deleted or rewritten: database triggers refuse it.
- HTTPS only (HSTS), strict Content-Security-Policy on the website and the API, secure HttpOnly refresh
  cookie, rate limits on login codes, reports and exports.

---

## 5. Backups

`deploy/backup.sh` writes a compressed database dump and an archive of uploaded files, with checksums, and
keeps 30 days. The database port is open to the server itself only (`127.0.0.1:5432`), so install the
PostgreSQL 16 client tools on the host (`apt install postgresql-client-16`) and run it nightly from cron:

```cron
30 2 * * * DATABASE_URL=postgres://vargani:<password>@127.0.0.1:5432/vargani MEDIA_ROOT=/var/lib/docker/volumes/vargani_media/_data BACKUP_DIR=/srv/backups/vargani BACKUP_S3_URI=s3://your-bucket/vargani /srv/vargani/deploy/backup.sh >> /var/log/vargani-backup.log 2>&1
```

(The volume path depends on the folder name you cloned into; `docker volume inspect vargani_media` shows it.)

Copy backups off the server (`BACKUP_S3_URI`); a backup on the same disk does not survive losing the server.
Also keep `deploy/.env` (especially `FIELD_ENCRYPTION_KEY`) in a password manager.

### Restore drill (do this monthly)

```bash
createdb -h 127.0.0.1 -U vargani vargani_restore_check
RESTORE_DATABASE_URL=postgres://vargani:<password>@127.0.0.1:5432/vargani_restore_check \
  ./deploy/restore.sh /srv/backups/vargani/<timestamp>
```

The script checks the checksums, refuses to touch a database that already has tables, restores everything in
one transaction (tables, data, triggers, row-level security) and prints the number of organizations,
payments, receipts and audit entries so you can compare them with the live site. Drop the check database
afterwards.

To recover after a disaster: restore into a new empty database, point `POSTGRES_DB` (or `DATABASE_URL`) at
it, unpack `media.tar.gz` into the media volume, and start the stack.

---

## 6. Updating to a new version

```bash
cd /srv/vargani
./deploy/backup.sh            # always back up first
git pull
docker compose -f docker-compose.prod.yml --env-file deploy/.env up -d --build
```

Migrations run automatically. The API is versioned under `/api/v1/`; changes stay backwards compatible so
installed mobile apps keep working.

---

## 7. Monitoring

| Check | URL / command |
|---|---|
| API alive | `GET /api/v1/health/` |
| API + database + Redis ready | `GET /api/v1/health/ready/` (point an uptime monitor such as UptimeRobot at it) |
| Logs | `docker compose -f docker-compose.prod.yml logs -f api worker` (one JSON object per line, with `request_id`) |
| Errors | Sentry, if `SENTRY_DSN` is set. Personal data is not sent. |

Every API response carries an `X-Request-ID` header; quote it when reporting a problem and find the matching
log lines with `grep <id>`.

---

## 8. Connecting the outside services

- **Razorpay**: each organization admin opens Settings → Online payments, pastes their key id, key secret and
  webhook secret, and adds the shown webhook URL in the Razorpay dashboard for the events `payment.captured`,
  `order.paid` and `payment.failed`.
- **MSG91**: create the DLT template, then the flow with variables `otp` and `minutes`; put the auth key and
  template id in `deploy/.env`.
- **Firebase**: see `docs/mobile/FLUTTERFLOW_GUIDE.md`, section 8.

---

## 9. Before going live checklist

- [ ] `deploy/.env` filled; secrets are new random values; a copy is stored safely off the server
- [ ] HTTPS works and `http://` redirects to `https://`
- [ ] Register, verify by SMS, create organization, add a person, collect a payment, download the receipt PDF
- [ ] Member login with a code on a real phone
- [ ] Nightly backup runs and is copied off the server; one restore drill done
- [ ] Uptime monitor on `/api/v1/health/ready/`
- [ ] Privacy policy published (draft in `docs/legal/`) and linked from the website and the Play Store listing
