# Building the Vargani mobile app in FlutterFlow

The Android (and later iOS) app is a FlutterFlow project that talks to the Vargani REST API. It has no
database of its own and no business rules of its own: every number, permission and receipt comes from the
API, so the app, the website and the reports always agree.

This guide walks through the FlutterFlow side step by step. Keep the Postman collection
(`docs/api/vargani.postman_collection.json`) open next to it: every call below is in it, ready to try.

---

## 1. What the app does

| Who opens it | What they see | Permission that unlocks it |
|---|---|---|
| Member | My contributions, dues, receipts, pay online, notifications | `portal.self` |
| Collector | Today's collection, my assigned people, collect a payment, share receipt on WhatsApp | `payments.create` |
| Treasurer / Admin | Dashboard, approvals, expenses (optional in v1) | `expenses.view`, `receipts.void_approve` |

Show or hide screens using the `permissions` map from `GET /api/v1/me/organizations/{id}/` (section 4).
The API checks every permission again on its side, so hiding is only for a clean UI.

---

## 2. Project setup

1. **Create the FlutterFlow project** (blank app). Package name, for example `in.vargani.app`.
2. **App State variables** (Settings → App State), all *persisted* except where noted:
   | Name | Type | Notes |
   |---|---|---|
   | `apiBase` | String | `https://api.your-domain.in` (no trailing slash) |
   | `accessToken` | String | not persisted, refreshed on start |
   | `refreshToken` | String | persisted; store with *Secure* storage enabled |
   | `orgId` | String | active organization |
   | `eventId` | String | active event |
   | `language` | String | `en`, `mr` or `hi` |
3. **Languages**: Settings → Languages → add English (`en`), Marathi (`mr`), Hindi (`hi`). Translate the
   app's own labels there. Text that comes from the API (notification text, error messages, report titles)
   is already translated by the server based on the `Accept-Language` header.
4. **Firebase**: connect a Firebase project (Settings → Firebase) and download `google-services.json`. The
   same Firebase project's service account is used by the backend for push (section 8).

---

## 3. The API group

Create one **API Group** called `Vargani` (API Calls → Add → Create API Group):

- Base URL: `[apiBase]/api/v1` (use the App State variable)
- Group headers:
  ```
  Authorization: Bearer [accessToken]
  X-Organization-ID: [orgId]
  Accept-Language: [language]
  X-Client-Type: app
  Content-Type: application/json
  ```

`X-Client-Type: app` makes login responses include the `refresh` token in the JSON body (the website gets it
as a secure cookie instead).

### Response and error format

- Successful responses are plain JSON objects; lists are paginated as
  `{"count": 42, "next": "...", "previous": null, "results": [...]}` (25 per page, `?page=2`).
- Errors always look like:
  ```json
  {"error": {"code": "validation_error", "message": "Some fields are invalid.",
             "details": {"amount": [{"code": "invalid", "message": "Amount must be more than zero."}]}},
   "request_id": "..."}
  ```
  Show `error.message` in a snackbar, and `error.details.<field>[0].message` under a form field.
  Nested fields follow the body: an error on the first payment line is at `error.details.lines.0.amount`.
- **Money is always a string** such as `"1100.50"`. Never convert it to a double for arithmetic; display it
  with a custom function that adds ₹ and Indian grouping (`₹1,10,000.50`).

---

## 4. Login and session

### 4a. Member login (mobile number + SMS code, no password)

1. `POST /auth/otp/request/` body `{"mobile": "9822001122"}` → always `200`
   `{"verification": {"destination": "98******22", "channel": "sms"}}`.
   The answer is the same whether or not the number is known, so it cannot be used to check who is a member.
2. `POST /auth/otp/verify/` body `{"mobile": "9822001122", "code": "123456"}` →
   `{"access": "...", "refresh": "...", "user": {...}}`.
   Save `access` and `refresh` in App State.

On first login the server creates the member's account and links it to their member record when exactly one
person in an organization (with the member portal switched on) has that mobile number. If a family shares a
phone number, the organization links the right person from the website (People → Portal login).

### 4b. Committee / collector login (email or mobile + password)

`POST /auth/login/` body `{"identifier": "...", "password": "..."}` → same token response.

### 4c. Keeping the session alive

- The access token lasts about 15 minutes. On app start, and whenever a call returns **401**, call
  `POST /auth/refresh/` with `{"refresh": "[refreshToken]"}`. The response contains a **new** `access` and a
  **new** `refresh` (tokens rotate); save both, then retry the original call once.
- If refresh also fails (400/401), clear the tokens and go to the login page.
- In FlutterFlow, do this in a small custom action `ensureFreshToken()` that you call in the
  *On Page Load* of the first page and in the *On Failure* branch of API calls.

### 4d. Logout

1. `POST /devices/unregister/` with `{"token": "<fcm token>"}` (stop push to this phone).
2. `POST /auth/logout/` with `{"refresh": "[refreshToken]"}` (the token is revoked on the server).
3. Clear App State.

### 4e. Choosing the organization

- `GET /me/organizations/` → `[{id, name, logo_url, role: {code, name}}]`.
  If there is one, select it automatically; if several, show a picker; save `orgId`.
- `GET /me/organizations/{orgId}/` → `{organization, role, permissions: {"payments.create": "assigned", ...},
  current_financial_year, member_portal_enabled}`.
  Keep `permissions` in a page/App State variable and use *Conditional visibility* with
  `permissions contains key "payments.create"`.
- If the list is empty after a member login, show: "Your login is not linked yet. Ask your organization to link
  your mobile number."

### 4f. Choosing the event

`GET /events/?status=active` → pick one (or the only one) and save `eventId`. Most screens send
`?event=[eventId]`.

---

## 5. Member screens

| Screen | Call | What to show |
|---|---|---|
| Home | `GET /portal/me/` | `person.full_name`, `organization.name`, `events[]`, and whether `online_payments` is on |
| Summary | `GET /portal/summary/?event=` | `total_paid`, `total_due`, `dues[]` (name, event, expected, paid, due) |
| Payments | `GET /portal/payments/?event=` | date `paid_at`, `amount`, `mode`, `lines[].contribution_type_name` |
| Receipts | `GET /portal/receipts/?event=` | `receipt_number`, `issued_at`, `amount`, `status` |
| Receipt PDF | `GET /portal/receipts/{id}/pdf/` | binary PDF (see below) |

Portal errors have a `code` you can switch on: `portal_not_linked` and `portal_unavailable`
(the organization switched the portal off).

**Opening a PDF**: API calls in FlutterFlow cannot return files, so add a custom action
`downloadPdf(url, fileName)` using the `http` and `open_filex` packages: GET the URL with the same
`Authorization` and `X-Organization-ID` headers, write the bytes to the temporary directory, then open it.

### Pay online (Razorpay)

Online payment is available when `GET /portal/me/` returns `"online_payments": true`.

1. Add the package `razorpay_flutter` (Settings → Project Dependencies) and a custom action `payOnline`.
2. `POST /portal/pay/` body
   `{"event": "[eventId]", "lines": [{"contribution_type": "<dues[i].contribution_type>", "amount": "1500.00"}]}` →
   `{"payment": "<id>", "checkout": {"key", "order_id", "amount", "currency", "name", "description", "prefill"}}`.
3. Open Razorpay with those values:
   ```dart
   _razorpay.open({
     'key': checkout['key'], 'order_id': checkout['order_id'], 'amount': checkout['amount'],
     'currency': checkout['currency'], 'name': checkout['name'], 'description': checkout['description'],
     'prefill': checkout['prefill'],
   });
   ```
4. On `EVENT_PAYMENT_SUCCESS`, call `POST /portal/pay/verify/` with
   `{"order_id": r.orderId, "payment_id": r.paymentId, "signature": r.signature}`.
   The response is the payment with its receipt. Refresh the summary and show "Payment received".
5. On `EVENT_PAYMENT_ERROR` show "The payment did not go through". Nothing is recorded as paid.

The receipt is issued only after the server checks Razorpay's signature (or receives Razorpay's webhook),
so a closed app or lost network in the middle never loses a payment and never creates a double receipt.
A `503` with code `gateway_unavailable` means the organization's gateway is not set up or Razorpay is down:
show the message and suggest paying the collector.

---

## 6. Collector screens

| Screen | Call |
|---|---|
| Today | `GET /collectors/me/dashboard/?event=` → `today`, `this_month`, `by_mode`, `assigned`, `recent_receipts[]` |
| My people | `GET /people/?search=&page=` (collectors only get people assigned to them) |
| Contribution types | `GET /contribution-types/?event=&is_active=true` |
| Collect | `POST /collections/` (below) |
| Share receipt | `POST /receipts/{id}/share/` → `whatsapp_url` (open it with *Launch URL*) |

### Recording a collection

```
POST /collections/
Idempotency-Key: <a new UUID for each collection screen>
{
  "event": "[eventId]",
  "payer": "<person id>",
  "mode": "cash",                 // cash, upi, bank_transfer, cheque, other
  "reference_number": "",         // required for upi / bank_transfer / cheque
  "lines": [
    {"contribution_type": "<id>", "amount": "500.00", "period_month": "2026-09-01"}
  ]
}
```

- `period_month` is only needed for monthly types (any day of the month; the server stores the 1st).
- **Generate the `Idempotency-Key` once when the screen opens** (custom function `uuid()`), not per tap. If
  the network drops and the collector taps Save again, the server returns the first payment instead of
  creating a duplicate. Generate a new key after a successful save.
- The response includes `receipt: {id, receipt_number}`. Go straight to a "Receipt issued" page with a big
  *Share on WhatsApp* button.

---

## 7. Notifications inside the app

| Call | Use |
|---|---|
| `GET /notifications/?page=` | list; each item has `title`, `body` (already in the user's language), `link`, `read_at`, `created_at`, `organization_name` |
| `GET /notifications/unread-count/` | badge on the bell icon |
| `POST /notifications/{id}/read/` | when tapped |
| `POST /notifications/read-all/` | "mark all read" |

`link` is a website path. Map it to app pages: `/app/my` → Member home, `/app/expenses` → Expenses,
`/app/approvals` → Approvals, `/app/receipts/{id}` → Receipt page.

The user's language for notifications and push is their profile language. When the user changes language in
the app, also call `PATCH /me/` with `{"preferred_language": "mr"}`.

---

## 8. Push notifications (Firebase Cloud Messaging)

The backend sends pushes itself through FCM; you do **not** need FlutterFlow's built-in push feature
(which needs its own Cloud Functions).

**App side**

1. Add packages `firebase_messaging` and `flutter_local_notifications`.
2. Custom action `registerForPush` (call it after login and on every app start when logged in):
   ```dart
   final messaging = FirebaseMessaging.instance;
   await messaging.requestPermission();
   final token = await messaging.getToken();
   // POST /devices/ {"token": token, "platform": "android", "app_version": "1.0.0"}
   messaging.onTokenRefresh.listen((t) { /* POST /devices/ again with the new token */ });
   ```
3. Create an Android notification channel with id `vargani_default` (the server uses it).
4. On notification tap, read `message.data`: `type`, `link`, `entity_type`, `entity_id`,
   `organization_id`, `notification_id`. Switch to `organization_id` if needed and open the page for `link`.
   Also call `POST /notifications/{notification_id}/read/`.

**Server side** (done once by whoever runs the backend)

1. Firebase console → Project settings → Service accounts → *Generate new private key*.
2. Put the JSON file on the server (never in git) and set:
   ```
   PUSH_BACKEND=fcm
   FCM_SERVICE_ACCOUNT_FILE=/run/secrets/fcm-service-account.json
   ```
3. Restart the API and the Celery worker. Tokens that Firebase reports as uninstalled are switched off
   automatically.

What gets pushed: receipt issued (to the member), dues reminders, expense sent for approval / approved /
rejected, receipt void requested / decided, failed online payment, and announcements.

---

## 9. Releasing on Google Play (you do this part)

1. FlutterFlow → Settings → App Details: app name *Vargani*, package name, version `1.0.0+1`, launcher icon.
2. Create an upload key and enable *Play App Signing* (FlutterFlow's Deploy → Android guides you).
3. Build an **App Bundle (.aab)** from FlutterFlow (or download the code and run `flutter build appbundle`).
4. Play Console → Create app → fill in:
   - **Privacy policy URL**: publish `docs/legal/PRIVACY_POLICY.md` on your website first.
   - **Data safety**: use `docs/legal/DATA_SAFETY.md` as the answers.
   - Content rating questionnaire, target audience (18+), app category *Finance* or *Productivity*.
5. Upload to the **Internal testing** track first, test with your committee for a week, then Closed →
   Production.
6. For every new backend release, keep the API backwards compatible (the API is versioned under `/api/v1/`).

---

## 10. Checklist before giving the app to members

- [ ] Login with OTP works on a real phone with a real SIM (SMS provider configured on the server).
- [ ] Token refresh works after leaving the app for 30 minutes.
- [ ] A member sees only their own payments and receipts.
- [ ] A collector sees only their assigned people (unless the organization allows open collection).
- [ ] Recording a collection twice with a bad network creates one payment only.
- [ ] Receipt PDF opens; WhatsApp share opens WhatsApp with the receipt link.
- [ ] Marathi and Hindi labels fit on small screens.
- [ ] Push arrives when the app is closed, and tapping it opens the right page.
- [ ] Razorpay test mode payment issues a receipt; a cancelled checkout does not.
