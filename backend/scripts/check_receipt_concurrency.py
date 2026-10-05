"""Concurrency check for receipt numbering (ROADMAP Phase 2 exit criterion).

Many collectors record payments at the same moment; every receipt must get a unique number with no gaps,
and a failed transaction must not burn a number.

This writes real money rows, which can never be deleted, so it runs only against a throwaway database:

    createdb vargani_concurrency
    DATABASE_URL=postgres://.../vargani_concurrency python manage.py migrate
    VARGANI_THROWAWAY_DB=1 DATABASE_URL=postgres://.../vargani_concurrency python scripts/check_receipt_concurrency.py
"""

import os
import sys
import threading
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django  # noqa: E402

django.setup()

from django.db import connection, transaction  # noqa: E402

from apps.accounts.models import User  # noqa: E402
from apps.contributions.models import ContributionType  # noqa: E402
from apps.events.models import Event  # noqa: E402
from apps.organizations import services as org_services  # noqa: E402
from apps.organizations.models import FinancialYear  # noqa: E402
from apps.payments.services import LineInput, record_payment  # noqa: E402
from apps.people.models import Person  # noqa: E402
from apps.receipts.models import Receipt  # noqa: E402

WORKERS = 20


class Boom(Exception):
    pass


def main():
    if os.environ.get("VARGANI_THROWAWAY_DB") != "1":
        sys.exit("Refusing to run: set VARGANI_THROWAWAY_DB=1 and point DATABASE_URL at a throwaway database.")

    suffix = os.urandom(3).hex()
    admin = User.objects.create_user(full_name="Concurrency", email=f"concurrency-{suffix}@example.com", password="x")
    org = org_services.create_organization(
        user=admin,
        name=f"Concurrency {suffix}",
        financial_year={"label": "2027–28", "start_date": date(2027, 4, 1), "end_date": date(2028, 3, 31)},
    )
    event = Event.objects.create(
        organization=org, financial_year=FinancialYear.objects.get(organization=org), name="Festival", code="CC"
    )
    ctype = ContributionType.objects.create(organization=org, event=event, name="Vargani")
    people = [Person.objects.create(organization=org, full_name=f"Person {i}") for i in range(WORKERS)]

    barrier = threading.Barrier(WORKERS)
    errors = []

    def worker(index):
        try:
            barrier.wait()
            if index % 5 == 0:
                # Fails after its receipt was numbered: the whole transaction, counter included, rolls back.
                try:
                    with transaction.atomic():
                        record_payment(
                            org=org,
                            event=event,
                            payer=people[index],
                            mode="cash",
                            lines=[LineInput(ctype, Decimal("10"))],
                        )
                        raise Boom()
                except Boom:
                    return
            record_payment(
                org=org, event=event, payer=people[index], mode="cash", lines=[LineInput(ctype, Decimal("100"))]
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(repr(exc))
        finally:
            connection.close()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(WORKERS)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    expected = WORKERS - len(range(0, WORKERS, 5))
    sequences = sorted(Receipt.objects.filter(organization=org).values_list("sequence", flat=True))
    numbers = set(Receipt.objects.filter(organization=org).values_list("receipt_number", flat=True))
    assert not errors, errors
    assert sequences == list(range(1, expected + 1)), f"gaps or duplicates: {sequences}"
    assert len(numbers) == expected
    print(f"OK: {expected} concurrent receipts numbered CC-2027-00001..{expected:05d}, no gaps, no duplicates")


if __name__ == "__main__":
    main()
