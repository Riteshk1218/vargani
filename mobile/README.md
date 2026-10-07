# Vargani mobile app (Flutter)

Android (and later iOS) app for collectors, committee members and members. It talks only to the
Vargani REST API (`/api/v1/`); there is no database and no business logic in the app. Every amount,
permission and receipt number comes from the server, so the app, the website and the reports agree.

## What it does

| Who | Screens |
|---|---|
| Collector / Karyakarta, Treasurer, Admin | Today's collection (today, week, month, total, by payment mode), assigned people with search, collect a payment (several contribution types in one payment, month for monthly Vargani, cash / UPI / bank / cheque / other with reference), receipt with **Share on WhatsApp** and **PDF**, receipts list |
| Member | Login with SMS code, total paid and total due, dues per contribution type, **Pay online** (Razorpay, when the organization has it switched on), payment history, receipts with PDF |
| Everyone | Organization switcher, event switcher, notifications with unread badge, English / मराठी / हिन्दी (saved on the phone and in the profile), log out |

Tabs are shown from the `permissions` the API returns for the selected organization. The API checks
every permission again, so hiding a tab is only for a clean screen.

Safety built in:
- Money is kept as the API's strings (`"1100.50"`), never as floating point.
- Each collection screen sends one `Idempotency-Key`, so tapping Save again after a network drop
  never records the payment twice.
- The refresh token is in encrypted storage; tokens rotate on every refresh and the session ends if
  refresh fails.
- Online payments are confirmed only by the server after it checks Razorpay's signature.

## Run it

```bash
flutter pub get
flutter test                       # 11 tests: API client, money, translations, collector and member flows
flutter run --dart-define=API_BASE=http://10.0.2.2:8000     # Android emulator -> API on your computer
```

`API_BASE` is the address of the API without `/api/v1`. It can also be changed on the login screen
(server icon), which is handy for testing.

## Build for Android

```bash
flutter build apk --release --dart-define=API_BASE=https://api.your-domain.in        # APK to install directly
flutter build appbundle --release --dart-define=API_BASE=https://api.your-domain.in  # .aab for Google Play
```

Release signing: create an upload key once and keep it safe (losing it means you cannot update the app):

```bash
keytool -genkey -v -keystore android/app/upload-keystore.jks -keyalg RSA -keysize 2048 -validity 10000 -alias upload
```

then create `android/key.properties` (never commit it):

```
storeFile=upload-keystore.jks
storePassword=...
keyAlias=upload
keyPassword=...
```

Without `key.properties` the release build is signed with the debug key: it installs on phones for
testing but Google Play will not accept it.

The GitHub workflow `.github/workflows/mobile.yml` runs the tests and builds both files on every push
to `mobile/`; download them from the run's *Artifacts*. Set the repository variable `API_BASE` and,
for Play Store builds, the secrets listed at the top of that file.

## Push notifications (optional, later)

The backend already sends pushes through Firebase (see `docs/mobile/FLUTTERFLOW_GUIDE.md`, section 8).
To receive them in this app: add the Firebase project's `google-services.json` to `android/app/`,
add the `firebase_core` and `firebase_messaging` packages, and after login call
`POST /api/v1/devices/` with the FCM token. Until then, notifications are visible in the app's
Alerts tab.

## FlutterFlow

The original plan was FlutterFlow. This app is plain Flutter, which is what FlutterFlow generates, so
it can be opened in Android Studio or VS Code directly. If you prefer to keep working in FlutterFlow,
`docs/mobile/FLUTTERFLOW_GUIDE.md` maps every screen here to the same API calls.

## Layout

```
lib/
  api/api_client.dart       headers, token refresh, error format
  state/app_state.dart      session, organization, event, language
  l10n/strings.dart         English / Marathi / Hindi labels
  util/                     money formatting, PDF opening, Razorpay checkout
  screens/                  login, organization picker, collector, member, receipts, alerts, settings
  widgets/common.dart       loading/error states, cards, event switcher
test/                       unit and widget tests (fake API with the real response shapes)
tool/seed_demo.py           creates a demo organization through the API (dev only)
tool/e2e.mjs                browser walkthrough of the web build against a real API (dev only)
```
