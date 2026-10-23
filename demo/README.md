# Try Vargani on your laptop

This runs the whole system on your own computer with a sample mandal already filled in, so you can
click around the website and the mobile app before anything goes live. Nothing is sent to anyone:
SMS codes are shown on screen and WhatsApp only opens with a ready message.

## One-time setup (Windows)

1. Install **Docker Desktop** from https://www.docker.com/products/docker-desktop/ and restart the
   laptop if it asks. Open Docker Desktop once and wait until it says *Engine running*.
2. Unzip `vargani-source.zip` into a folder, for example `Documents\vargani`.

## Start

Open the `demo` folder and double-click **START-DEMO**. The first time it downloads about 1.5 GB and
takes 5 to 15 minutes; after that it starts in under a minute. When it is ready, two browser tabs open:

| What | Address | Log in with |
|---|---|---|
| Website (committee) | http://localhost:8080 | `admin@demo.test`, password `DemoPass#2026` |
| Mobile app (collector) | http://localhost:8081 | `collector@demo.test`, password `DemoPass#2026` |
| Platform owner (super admin) | http://localhost:8080/platform (raw screens: `/django-admin/`) | `superadmin@demo.test`, password `DemoPass#2026` |
| Mobile app (member) | http://localhost:8081 → **Member** tab | mobile `9822001122`, tap *Send code* (the code fills in by itself) |

The mobile app runs in the browser here. To see it at phone size in Chrome, press `F12` and then
`Ctrl+Shift+M`.

## Try it on your phone

Your phone must be on the same Wi-Fi as the laptop.

1. On the laptop, open *Command Prompt*, type `ipconfig` and note the **IPv4 Address**, for example
   `192.168.1.25`.
2. On the phone, open Chrome and go to `http://192.168.1.25:8081` (your own number, then `:8081`).
   The website works the same way on `:8080`.
3. If the phone cannot open it, Windows Firewall is blocking it: when Windows asks whether to allow
   Docker, choose *Allow*.

## Things to try

- **Collector:** People → Ritesh Patil → enter any amount → Save → Share on WhatsApp / Open PDF.
- **Collect without a name:** Collect → Contributor → **No name** (or **New person** to add someone on
  the spot). The receipt shows the event, financial year, date and exact time.
- **Expenses (collector):** Expenses tab → Add expense → category, purpose, amount, bill photo →
  Submit for approval.
- **Expenses (committee):** website → Expenses → open one → Approve or Reject (with a reason). Only
  approved expenses count.
- **Financial summary:** website menu → Financial summary: Collection − Approved expenses = Balance,
  per event and financial year. The admin also sees it on the mobile Home screen.
- **Admin edit and delete:** website → Payments → open a payment → Edit or Delete. Edits keep the
  receipt number; a deleted payment leaves the lists and totals but stays in the audit log.
- **Website:** see payments on the Dashboard, Receipts and Reports; add an event, a person or an
  expense; change the language at the top to मराठी or हिन्दी.
- **Member:** log in as Ritesh with `9822001122`: he sees only his own payments, dues and receipts.

## Stop or start again

- **STOP-DEMO** stops it. Everything you entered is kept for next time.
- **RESET-DEMO** deletes everything you entered and gives you fresh sample data next time.

This demo uses fixed test passwords and keys. It is only for trying things out on your laptop, never
for the live site (that is `docs/deploy/DEPLOYMENT.md`).
