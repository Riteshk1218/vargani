# Vargani — Contribution Management Platform

One platform for any organization that collects contributions (Ganeshotsav mandals, temples, societies, trusts, NGOs, clubs). Each organization's data is fully separate.

- `backend/` — Django REST API at `/api/v1/` (the only way to the data, for the website and the FlutterFlow app)
- `frontend/` — React + TypeScript website
- `mobile/` — Flutter mobile app (Android, iOS later)
- `demo/` — one-click local demo with sample data
- Architecture, database, API and roadmap docs: `architecture/` in the project files

## Status

**Phase 1:** sign up / sign in (email or mobile + OTP), create organization, logo, financial years, invite users with roles, events, people, language switch (English, मराठी, हिंदी), audit log.

**Phase 2:** funds and contribution types per event, recording collections (flexible amounts, several months or types in one payment, cash / UPI / bank / cheque, pending cheques), automatic gapless receipt numbers (`GC-2026-00001`), printable receipts in the organization's receipt language, payments, contributions and dues lists, and dashboard totals. Money rows can't be deleted or rewritten (database triggers), except through the admin edit and delete below, which are audited.

**Phase 3:** receipt PDFs, WhatsApp sharing, void and correction requests with approval, collector assignments.

**Phase 4:** expenses with bill uploads and approval, other income, 14 reports (collections by month, fund, mode and collector, dues, receipts, expenses, income and expenditure, audit and more) with CSV, Excel and PDF export, audit log screen.

**Phase 5:** member portal (members log in with a mobile code and see only their own dues, payments and receipts), online payments through each organization's own Razorpay account, in-app notifications in the reader's language, announcements, monthly dues reminders.

**Phase 6:** push notifications (Firebase), device registration, OpenAPI file and Postman collection, FlutterFlow guide.

**Phase 7:** database row-level security per organization, production settings, JSON logs, security headers, MSG91/Twilio SMS, Docker production stack with automatic HTTPS, backup and restore scripts, privacy policy and Play Store data-safety drafts.

**Phase 8:** the contributor is optional (pick an existing person, add a new person on the spot, or record it as Anonymous); every collection and expense records the event, financial year, date and exact time, shown on receipts and lists; collectors add expenses with a bill photo and submit them for approval; a financial summary per event and financial year (collection − approved expenses = balance); the organization admin can edit or delete collections (the receipt keeps its number; a deleted one is voided and kept in the audit log), expenses, other income and events.

## Documents

| What | Where |
|---|---|
| Deploying to a server | `docs/deploy/DEPLOYMENT.md` |
| Running it for free (Oracle Always Free, DuckDNS, Gmail, APK) and what each paid extra costs | `docs/deploy/FREE-HOSTING.md` |
| Building the mobile app in FlutterFlow | `docs/mobile/FLUTTERFLOW_GUIDE.md` |
| API contract (OpenAPI, Postman) | `docs/api/` |
| Privacy policy and Play Store data-safety drafts | `docs/legal/` (have them reviewed before publishing) |

## Try it on your laptop

Double-click `demo/START-DEMO.bat` (needs Docker Desktop): website on http://localhost:8080 and the mobile app on
http://localhost:8081, with a sample mandal and logins. Steps in `demo/README.md`.

## Quick start (Docker)

```bash
cp backend/.env.example backend/.env      # edit DJANGO_SECRET_KEY
docker compose up --build
```

Open http://localhost:5173 and click **Create account**. In development the OTP code is shown on screen (and printed in the backend log).

API docs: http://localhost:8000/api/v1/docs/

## Quick start (without Docker)

Needs Python 3.12+, Node 20+, PostgreSQL 15+ and Redis.

```bash
# backend
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver

# website (second terminal)
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Tests

```bash
cd backend && pytest          # isolation, permissions, money rules, auth, organizations, events, people
# receipt numbering under concurrency (needs a throwaway database; see the script header)
VARGANI_THROWAWAY_DB=1 DATABASE_URL=postgres://.../throwaway python scripts/check_receipt_concurrency.py
cd frontend && npm test && npm run typecheck
```

## Mobile app (FlutterFlow)

FlutterFlow talks only to the REST API, never to the database:

1. Base URL `https://<your-domain>/api/v1`.
2. `POST /auth/login/` with `{"identifier", "password"}` returns `access` and `refresh`. Send `Authorization: Bearer <access>` on every call; refresh with `POST /auth/refresh/ {"refresh"}`.
3. `GET /me/organizations/` lists the user's organizations. Send `X-Organization-ID: <id>` on every organization call.
4. Record a collection with `POST /collections/` and an `Idempotency-Key` header (a fresh UUID per attempt), so a retry on a bad network never records the money twice. The response includes the receipt number.
5. All errors look like `{"error": {"code", "message", "details"}, "request_id"}`. Send `Accept-Language: mr` or `hi` for translated messages.

The full contract is at `/api/v1/schema/` (OpenAPI) and `/api/v1/docs/`. The step-by-step guide is `docs/mobile/FLUTTERFLOW_GUIDE.md`.
