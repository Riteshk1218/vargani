# Google Play "Data safety" answers (DRAFT)

> Draft answers for the Play Console *Data safety* form, based on what the Vargani app and API actually do.
> Review them against your final app (especially any extra SDKs you add in FlutterFlow, such as analytics or
> crash reporting, which must be declared too) before submitting.

## Overview questions

| Question | Answer |
|---|---|
| Does your app collect or share any of the required user data types? | **Yes** |
| Is all of the user data collected by your app encrypted in transit? | **Yes** (HTTPS only) |
| Do you provide a way for users to request that their data is deleted? | **Yes**: in-app request to the organization / Grievance Officer email (financial records are retained as required by law; say so in the policy) |
| Privacy policy URL | `https://[your domain]/privacy` (publish `PRIVACY_POLICY.md` there) |

## Data types

For each, Play asks: *collected?*, *shared?*, *processed ephemerally?*, *required or optional?*, *purposes*.

| Category → type | Collected | Shared* | Required? | Purposes |
|---|---|---|---|---|
| Personal info → Name | Yes | No | Required | App functionality, Account management |
| Personal info → Email address | Yes | No | Optional | Account management, App functionality |
| Personal info → Phone number | Yes | No | Required | Account management (login code), App functionality |
| Personal info → Address | Yes | No | Optional | App functionality (organization's member records) |
| Financial info → Purchase history | Yes (contributions, receipts) | No | Required | App functionality |
| Financial info → Other financial info | Yes (dues, payment references) | No | Required | App functionality |
| Financial info → Payment info (card/UPI) | **No** (handled by Razorpay's own SDK; declare Razorpay's collection per their guidance) | — | — | — |
| Photos and videos → Photos | Yes, only if a committee user uploads a bill photo | No | Optional | App functionality |
| Files and docs | Yes, only if a committee user uploads a bill PDF | No | Optional | App functionality |
| App activity → Other actions | Yes (audit log of changes) | No | Required | App functionality, Fraud prevention / security |
| App info and performance → Crash logs | Only if you enable crash reporting | No | Optional | Analytics |
| Device or other IDs | Yes (push notification token) | No | Optional | App functionality (notifications) |

\* "Shared" in Play's sense excludes service providers processing data on your behalf (hosting, SMS,
Firebase Cloud Messaging), so those are **not** declared as sharing.

Not collected: location, contacts, messages, health, web browsing, audio, calendar, precise or approximate
location, advertising ID.

## Security practices section

- Data is encrypted in transit: **Yes**
- Users can request data deletion: **Yes**
- Committed to follow the Play Families Policy: **No** (not designed for children)
- Independent security review: **No** (unless you commission one)
