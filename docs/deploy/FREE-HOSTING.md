# Running Vargani for free (or almost free)

Short answer: **yes, you can run the website, the API and the database for ₹0 a month**, and give the
Android app to your committee for free as an APK file. Money is only needed for extras: your own domain
name, SMS login codes for members, and the Play Store listing.

Prices below are approximate (October 2026) and can change; check each provider's page before paying.

---

## What it costs

| Part | Free way | Paid way (if you want it) |
|---|---|---|
| Website + API + database + background jobs | **Oracle Cloud "Always Free" server: ₹0** | Small VPS in India: about ₹500–1,200 a month |
| Web address | **Free DuckDNS name**, e.g. `ourmandal.duckdns.org` | Your own `.in` / `.com`: about ₹500–1,000 a year |
| HTTPS (padlock) | **Free**, automatic (Let's Encrypt, already set up) | — |
| Emails (sign-up codes, invitations, password reset) | **Gmail with an app password** (about 500 a day) or Brevo free plan (300 a day) | — |
| Member login by SMS code | Switch SMS off: committee logs in with email + password, members get receipts on WhatsApp | MSG91: about ₹0.20–0.30 per SMS, plus a one-time DLT registration with an operator |
| WhatsApp receipt sharing | **Free** (uses the collector's own WhatsApp) | — |
| Android app file (APK) | **Free**: built by GitHub, shared by link or WhatsApp | — |
| Play Store listing | — | Google Play developer account: US$25 once (about ₹2,100) |
| iPhone app | — | Apple developer account: US$99 a year |
| Online payments | — | Razorpay: no setup fee, about 2% of each online payment |
| Push notifications | **Free** (Firebase) | — |
| Backups | **Free**: nightly backup to the server's disk; Oracle also gives free object storage | — |

**No card?** Oracle needs a card for its identity check. Without one, use **Render + Neon + Brevo** instead:
also ₹0 and no card, but the site sleeps when nobody uses it (about a minute to wake up). Steps in
[`RENDER.md`](RENDER.md).

So the **₹0 setup** is: Oracle server + DuckDNS name + Gmail for emails + SMS switched off + APK shared
directly. The **cheapest "proper" setup** adds a `.in` domain (about ₹700 a year) and the Play Store
(₹2,100 once).

### Why not Render, Railway or Vercel free plans?

Vargani needs five things running all the time: the API, a background worker, a scheduler, PostgreSQL and
Redis. On those free plans the server falls asleep, and free databases are deleted after a few weeks.
That is not safe for money records. One Oracle free server runs all five together.

---

## Free setup, step by step

### 1. Get the free server (Oracle Cloud)

1. Sign up at https://www.oracle.com/cloud/free/. A debit or credit card is needed only to check who you
   are; Always Free resources are not charged. Choose **India West (Mumbai)** or **India South
   (Hyderabad)** as the home region (it can't be changed later).
2. Create a VM: **Compute → Instances → Create instance**.
   - Image: **Ubuntu 24.04**
   - Shape: **Ampere (VM.Standard.A1.Flex)**, 2 OCPU and 12 GB memory (free up to 4 OCPU / 24 GB in total)
   - Boot volume: 100 GB (free up to 200 GB in total)
   - Download the SSH key it offers, and keep it safe.
   - If it says *Out of capacity*, try again later or pick another availability domain.
3. Open the web ports: on the instance page click the **subnet → Default Security List → Add Ingress
   Rules**, source `0.0.0.0/0`, TCP, destination ports **80** and **443**.
4. Note the server's **public IP address**.

Good to know: Oracle may reclaim an Always Free server that sits almost completely idle for a week. A
running Vargani normally keeps it busy enough. Upgrading the account to "Pay As You Go" removes that
rule and still costs nothing as long as you stay inside the free limits.

### 2. Get a free web address (DuckDNS)

1. Go to https://www.duckdns.org and sign in with Google.
2. Type a name, e.g. `ourmandal`, and click **add domain**.
3. Put the server's public IP in the **current ip** box and click **update ip**.

Your address is now `ourmandal.duckdns.org`. (With a bought domain, add an **A record** pointing to the
IP instead.)

### 3. Get free email sending (Gmail)

1. Use a Gmail account for the mandal. Turn on **2-Step Verification** (Google Account → Security).
2. Create an **App password** (Google Account → Security → App passwords), name it "Vargani", and copy the
   16-letter password.

### 4. Install Vargani on the server

Connect to the server (Oracle's **Cloud Shell** or any SSH app) as `ubuntu`, then:

```bash
sudo iptables -I INPUT 6 -p tcp -m multiport --dports 80,443 -j ACCEPT && sudo netfilter-persistent save
curl -fsSL https://get.docker.com | sudo sh && sudo usermod -aG docker ubuntu && newgrp docker
git clone https://github.com/<your-github-name>/vargani.git ~/vargani && cd ~/vargani
cp deploy/.env.example deploy/.env
nano deploy/.env
```

In `deploy/.env` set (use your own DuckDNS name):

```ini
DOMAIN=ourmandal.duckdns.org
DJANGO_ALLOWED_HOSTS=ourmandal.duckdns.org
CORS_ALLOWED_ORIGINS=https://ourmandal.duckdns.org
CSRF_TRUSTED_ORIGINS=https://ourmandal.duckdns.org
FRONTEND_URL=https://ourmandal.duckdns.org
API_PUBLIC_URL=https://ourmandal.duckdns.org

# Free setup: no SMS. People sign up and log in with email + password.
SMS_BACKEND=apps.accounts.sms.DisabledSMSBackend

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=yourmandal@gmail.com
EMAIL_HOST_PASSWORD=<the 16-letter app password>
DEFAULT_FROM_EMAIL=Vargani <yourmandal@gmail.com>
```

Fill the secret values too. These commands print fresh ones:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"     # run twice: DJANGO_SECRET_KEY, JWT_SIGNING_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(24))"     # run twice: POSTGRES_PASSWORD, POSTGRES_ADMIN_PASSWORD
docker run --rm python:3.12-slim sh -c "pip -q install cryptography && python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"   # FIELD_ENCRYPTION_KEY
```

Save a copy of `deploy/.env` somewhere safe (not on GitHub). Then start everything:

```bash
docker compose -f docker-compose.prod.yml --env-file deploy/.env up -d --build
```

The first start takes 10–20 minutes. Then open `https://ourmandal.duckdns.org`, click **Register**, and
create your organization. The first person becomes the Organization Admin.

Turn on nightly backups (section 5 of `DEPLOYMENT.md`):

```bash
(crontab -l 2>/dev/null; echo "30 2 * * * cd ~/vargani && ./deploy/backup.sh >> ~/backup.log 2>&1") | crontab -
```

### 5. Get the Android app (free)

1. Put the code on GitHub (private repository). GitHub's free plan includes build minutes for this.
2. In the repository: **Settings → Secrets and variables → Actions → Variables → New variable**,
   name `API_BASE`, value `https://ourmandal.duckdns.org`.
3. **Actions → Mobile app → Run workflow**. After about 10 minutes, open the finished run and download
   **vargani-android** from *Artifacts*. Inside is `app-release.apk`.
4. Send the APK to collectors on WhatsApp or Google Drive. On the phone they tap it and allow
   *Install unknown apps* once.

For the Play Store later: create the signing key (see `mobile/README.md`), add it as the four
`ANDROID_KEY…` secrets, run the build again, and upload `app-release.aab` in the Play Console.

---

## Switching SMS on later

When you want members to log in with a mobile code:

1. Open an MSG91 account, finish DLT registration, and get an OTP template approved
   (variables `otp` and `minutes`).
2. In `deploy/.env` change `SMS_BACKEND=apps.accounts.sms.MSG91SMSBackend` and fill
   `SMS_MSG91_AUTH_KEY` and `SMS_MSG91_TEMPLATE_ID`.
3. Restart: `docker compose -f docker-compose.prod.yml --env-file deploy/.env up -d`.

While SMS is off, asking for a code on a mobile number shows a clear message ("Login codes by SMS are not
switched on yet. Use your email address.") instead of a code that never arrives. Everything else works:
collections, receipts, PDF, WhatsApp sharing, expenses, reports.
