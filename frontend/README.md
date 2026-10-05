# Vargani website

React + TypeScript + Vite + Tailwind. Talks to the Django API only.

```bash
npm install
cp .env.example .env
npm run dev          # http://localhost:5173, proxies /api to http://localhost:8000
npm test             # vitest
npm run typecheck
npm run build
```

- `src/services/` API calls (`apiClient.ts` handles tokens and the `X-Organization-ID` header)
- `src/context/` signed-in user, active organization, active event
- `src/pages/` screens; `src/components/` shared UI
- `src/i18n/locales/{en,mr,hi}/common.json` translations; a test checks all three have the same keys

In production set `VITE_API_BASE_URL` if the API lives on another domain.
