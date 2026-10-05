# Privacy Policy (DRAFT)

> **Draft for review.** This text describes what the Vargani software actually does with personal data, so
> that whoever operates it has an accurate starting point. It is not legal advice. Have it reviewed by a
> lawyer familiar with India's Digital Personal Data Protection Act, 2023 (DPDP Act) before publishing, and
> replace every `[placeholder]`.

**Last updated:** [date]

This policy explains how **[Operator name]** ("we") handles personal data in the Vargani website and mobile
app ("Vargani"). Vargani helps organizations such as Ganeshotsav mandals, trusts, housing societies and
associations record contributions, issue receipts and keep accounts.

## 1. Who is responsible

- Each **organization** using Vargani (for example, your mandal or society) decides whose details are recorded
  and why. For the details of its members and contributors, the organization is the *Data Fiduciary*.
- **[Operator name]** runs the Vargani service and processes that data on the organizations' behalf, and is
  the Data Fiduciary for the accounts of people who sign up to use Vargani.

Contact / Grievance Officer: **[name]**, **[email]**, **[address]**. We respond within **[30]** days.

## 2. What we collect

| Data | From whom | Why |
|---|---|---|
| Name, mobile number, email address | users who sign up; people added by an organization | identify the person, log in, send receipts and login codes |
| Address details (flat/unit, building, area, city, PIN code) | added by the organization | identify households, assign collectors |
| Contributions, payments, receipts, dues | recorded by the organization or paid online | the organization's accounts and receipts |
| Expenses and bills (photos/PDFs) | uploaded by the organization's committee | the organization's accounts |
| Preferred language | the user | show the app and messages in English, Marathi or Hindi |
| Login records: time, IP address, device type | automatically | security and the audit log |
| Push notification token | the mobile app, if you allow notifications | send you notifications |

We do **not** collect card numbers, UPI PINs or bank passwords. Online payments are handled by Razorpay on
its own secure pages; we receive only the payment reference, amount and status.

We do not use your data for advertising and we do not sell it.

## 3. How data is used

- To run the organization's contribution records, receipts, reports and accounts.
- To let you log in (a one-time code sent by SMS or email).
- To show members their own contributions and receipts in the member portal and app.
- To send notifications you would expect: receipts, reminders of dues, approvals, announcements from your
  organization.
- To keep an audit log of who changed what, which organizations need for transparent accounts.
- To keep the service secure and fix problems.

## 4. Who can see your data

- **Your organization's committee**, according to their role (for example, a collector sees only the people
  assigned to them; a member sees only their own records).
- **Other organizations cannot see it.** Each organization's data is kept separate, and the database itself
  enforces this.
- **Service providers** that help us run Vargani, only for that purpose:
  - Hosting: **[hosting provider, region e.g. AWS Mumbai]**
  - SMS: **[MSG91 / other]** (your mobile number and the login code)
  - Email: **[provider]**
  - Online payments: **Razorpay** (when you choose to pay online)
  - Push notifications: **Google Firebase Cloud Messaging** (device token and notification text)
  - Error tracking (if enabled): **[Sentry]**, configured not to send personal data
- Authorities, when the law requires it.

## 5. How long we keep it

- **Financial records** (contributions, payments, receipts, expenses, other income) and the **audit log** are
  kept for as long as the organization needs them for its accounts and as required by law
  (**[e.g. 8 years]**). They cannot be deleted from the system, only marked as cancelled or void, so that
  accounts stay complete and trustworthy.
- A person's contact details can be **archived** by the organization when they are no longer active.
- Login codes expire after 5 minutes. Push tokens are removed when you log out or uninstall the app.
- Backups are kept for **[30]** days.

## 6. Your rights

Under the DPDP Act you can ask to:
- see the personal data held about you,
- correct or update it,
- have it erased where it is no longer needed and no law requires keeping it (financial records the
  organization must keep are retained, but can be restricted),
- withdraw consent for optional processing (for example, notifications), and
- nominate someone to exercise these rights for you.

Ask your organization first for records it keeps about you, or contact our Grievance Officer. If you are not
satisfied, you may complain to the Data Protection Board of India.

## 7. Security

HTTPS everywhere; passwords stored with Argon2 hashing; one-time codes with limits on attempts; data separated
per organization at the database level; payment gateway secrets encrypted; every change recorded in an audit
log that cannot be edited; nightly encrypted off-site backups. No system is perfectly secure; if a breach
affects you, we will inform you and the Data Protection Board as the law requires.

## 8. Children

Vargani is meant for adults managing their organization's accounts. Children's contributions may be recorded
by an organization under a parent's or guardian's name; children should not create accounts.

## 9. Changes

We will post changes here and update the date above. Significant changes will be notified in the app.
