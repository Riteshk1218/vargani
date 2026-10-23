# Free hosting without a card: Render + Neon + Brevo

This puts the website and the API online for ₹0 with no credit or debit card:

| Part | Service | Free plan |
|---|---|---|
| Website + API | **Render** (web service, Docker) | Sleeps after 15 minutes without visitors; the next visit takes about a minute to wake it |
| Database (and uploaded files) | **Neon** (PostgreSQL) | 1 GB, no card, never expires |
| Emails (sign-up codes, invitations, password reset) | **Brevo** | 300 emails a day |

It uses `render.yaml` and `Dockerfile.render` from this repository: one service that serves the website and
the API together, keeps uploaded files (logos, bill photos, report exports) in the database, and runs
background jobs straight away instead of in a separate worker.

**Limits compared with a full server:** the first visit after a quiet spell is slow; the automatic monthly
dues reminders don't run (send reminders from the website instead); SMS login codes stay off; and the
database plus files must fit in 1 GB (bill photos are shrunk to about 0.5 MB each, so that is thousands of
bills). Move to a paid server with `DEPLOYMENT.md` whenever you outgrow it: the code is the same.

---

## 1. Neon: the database (5 minutes)

1. Go to https://neon.tech and click **Sign up**. Choose **Continue with GitHub** (or Google).
2. Create a project:
   - Name: `vargani`
   - Region: **AWS Asia Pacific (Singapore)**
   - Leave the rest as it is and click **Create project**.
3. On the project page, click **Connect**. Copy the **connection string**. It looks like
   `postgresql://neondb_owner:abc123@ep-...aws.neon.tech/neondb?sslmode=require`.
   Keep it somewhere private for step 3. It is a password: don't post it anywhere.

## 2. Brevo: emails (5 minutes, sometimes a few hours for approval)

1. Go to https://www.brevo.com and click **Sign up free**. Use the mandal's email address.
2. Fill in the short profile. If Brevo asks, confirm your mobile number.
3. Add the sender: **Settings → Senders, domains & dedicated IPs → Senders → Add a sender**. Use the same
   email address, then click the link Brevo emails you.
4. Get the SMTP login: **Settings → SMTP & API → SMTP** tab. Note the **Login** (looks like
   `9a1b2c001@smtp-brevo.com`), then click **Generate a new SMTP key** and copy it.

## 3. Render: put it online (10 minutes, then about 15 minutes of building)

1. Go to https://render.com and click **Get Started**. Choose **GitHub** and allow access.
2. Click **New +** → **Blueprint**.
3. Pick the **vargani** repository. Render reads `render.yaml` and shows one service called **vargani**.
4. It asks for six values:

   | Name | What to paste |
   |---|---|
   | `DATABASE_ADMIN_URL` | the Neon connection string from step 1 |
   | `EMAIL_HOST_USER` | the Brevo SMTP **Login** |
   | `EMAIL_HOST_PASSWORD` | the Brevo **SMTP key** |
   | `DEFAULT_FROM_EMAIL` | `Vargani <the sender email you added in Brevo>` |
   | `DJANGO_SUPERUSER_EMAIL` | your email, for the **Platform Admin** login at `/django-admin/` |
   | `DJANGO_SUPERUSER_PASSWORD` | a strong password for that login (at least 10 characters, not used elsewhere) |

5. Click **Apply** (or **Deploy Blueprint**). The first build takes 10–20 minutes. When the service shows
   **Live**, its address is at the top, for example `https://vargani.onrender.com`. If the name was taken,
   Render adds a few letters, e.g. `https://vargani-ab12.onrender.com`.
6. Open the address, click **Register**, and create your organization. The first person becomes the
   Organization Admin. The sign-up code arrives by email.

Every push to the `main` branch on GitHub redeploys automatically.

### Two kinds of admin

- **Organization Admin** (runs one mandal): whoever registers on the website and creates the organization.
  Everything for that mandal is on the website: people, collections, receipts, expenses, reports, users and
  roles, settings.
- **Platform Admin** (you, running the whole platform): log in on the website with `DJANGO_SUPERUSER_EMAIL`
  and its password. You land on the **Platform owner** page (also in the profile menu), which lists every
  organization with its admins and counts of users, people, events and receipts, and every login with the
  organizations and roles it has. From there you can create a new organization together with its admin's
  login and password (for a new mandal that buys the app), suspend or reactivate an organization, set a new
  password for a user who is locked out, and block or unblock a login. It deliberately shows no money
  records or member details of any mandal. To see a mandal's data, the platform admin must be added to that
  organization like anyone else. The raw database screens stay at `https://<your address>/django-admin/`.

An Organization Admin adds a user on **Users & Roles → Add user** by typing their name, mobile or email, a
password and a role; the website then shows the login details to copy or send on WhatsApp. **Invite by link**
is still there for people who should choose their own password. The admin can also **Set password** for a
user whose login belongs only to that organization.

### Keeping it awake (optional)

So people don't wait a minute after a quiet spell, a free monitor can visit the site every 10 minutes:

1. Sign up at https://uptimerobot.com (free, no card).
2. **Add New Monitor** → type **HTTP(s)**, URL `https://<your address>/api/v1/health/`, interval **10 minutes**.

Render's free plan includes 750 hours a month, enough to stay awake all month for one service. This health
address doesn't touch the database, so Neon's free hours aren't used up by it.

---

## 4. The Android app

Tell Claude (or your developer) the Render address. The app is then rebuilt to use it: in the GitHub
repository, **Settings → Secrets and variables → Actions → Variables**, set `API_BASE` to the address
(e.g. `https://vargani.onrender.com`), then **Actions → Mobile app → Run workflow**, and download
**vargani-android** from the finished run.

---

## How it works (for developers)

- `Dockerfile.render` builds the React site and the Django API into one image. Django serves the site
  (WhiteNoise for files, `apps/core/website.py` for pages, with the same security headers as
  `deploy/nginx.conf`).
- `STORAGE_BACKEND=database` stores uploads in the `core_storedfile` table (`apps/core/storage.py`). Only
  organization logos are public (`/media/orgs/<id>/logo/<hex>.png`); bills and exports go through the API.
- `CACHE_BACKEND=locmem` and `CELERY_TASK_ALWAYS_EAGER=true` remove the need for Redis and a worker.
- With only `DATABASE_ADMIN_URL` set, `manage.py ensure_app_role` creates the `vargani_app` role (no
  superuser, no BYPASSRLS; password derived from the secret key) and the app connects as that role, so
  row-level security between organizations still applies. Neon's pooled host is swapped for the direct
  one (`config/dburl.py`).
- Render's free plan blocks outgoing mail ports 465 and 587, so email goes to Brevo on port 2525.
- Render's generated `FIELD_ENCRYPTION_KEY` is not a Fernet key; `apps/gateway/crypto.py` derives one
  from it. Don't change that value later, or saved Razorpay secrets must be entered again.
