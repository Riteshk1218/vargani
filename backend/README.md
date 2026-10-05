# Vargani API (Django)

```bash
pip install -r requirements-dev.txt
cp .env.example .env
python manage.py migrate      # also syncs permissions and system roles
python manage.py runserver
pytest
ruff check .
```

Apps in `apps/`: `core` (tenancy, permissions, errors), `accounts`, `organizations`, `people`, `events`, `audit`, `reports`.

Rules every new endpoint follows:

- Subclass `TenantModelViewSet` and set `required_permissions`; never query tenant models without `for_org(...)`.
- No DELETE endpoints. Financial records are cancelled or voided, never deleted.
- Money is `Decimal`; IDs are UUID v7.
- New user-facing messages go through `gettext`; add Marathi and Hindi in `locale/translations.py` and run it, then `compilemessages`.
- `tests/` in `core` walks every route to check isolation and the no-delete rule; keep it green.
