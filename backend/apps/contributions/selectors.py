"""Read-side aggregates for contributions. Every function takes an already org-scoped queryset or object."""

from datetime import date
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth

from apps.events.models import EventParticipant
from apps.payments.models import Payment

from .models import Contribution, ContributionType

ZERO = Decimal("0.00")


def _money(value) -> str:
    return f"{(value or ZERO):.2f}"


def summarize(lines, payments) -> dict:
    """Totals for confirmed contribution lines and successful payments (both already scoped)."""
    lines = lines.filter(status=Contribution.Status.CONFIRMED)
    payments = payments.filter(status=Payment.Status.SUCCESSFUL)
    totals = lines.aggregate(total=Sum("amount"), contributors=Count("person", distinct=True))
    by_type = (
        lines.values("contribution_type", "contribution_type__name")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")
    )
    by_fund = lines.values("fund", "fund__name").annotate(total=Sum("amount")).order_by("-total")
    by_month = (
        lines.annotate(month=TruncMonth("contributed_on"))
        .values("month")
        .annotate(total=Sum("amount"))
        .order_by("month")
    )
    by_mode = payments.values("mode").annotate(total=Sum("amount"), count=Count("id")).order_by("-total")
    return {
        "collected": _money(totals["total"]),
        "contributors": totals["contributors"] or 0,
        "payments": payments.count(),
        "by_type": [
            {
                "id": str(r["contribution_type"]),
                "name": r["contribution_type__name"],
                "total": _money(r["total"]),
                "count": r["count"],
            }
            for r in by_type
        ],
        "by_fund": [
            {"id": str(r["fund"]) if r["fund"] else None, "name": r["fund__name"], "total": _money(r["total"])}
            for r in by_fund
        ],
        "by_month": [{"month": r["month"].strftime("%Y-%m"), "total": _money(r["total"])} for r in by_month],
        "by_mode": [{"mode": r["mode"], "total": _money(r["total"]), "count": r["count"]} for r in by_mode],
    }


def months_between(start: date, end: date) -> int:
    if end < start:
        return 0
    return (end.year - start.year) * 12 + end.month - start.month + 1


def expected_per_person(ctype: ContributionType, today: date) -> Decimal:
    if not ctype.is_mandatory or ctype.target_amount is None:
        return ZERO
    if ctype.kind == ContributionType.Kind.ONE_TIME:
        return ctype.target_amount
    event = ctype.event
    start = ctype.start_date or event.start_date or ctype.created_at.date()
    end = min(d for d in (today, ctype.end_date, event.end_date) if d is not None)
    return ctype.target_amount * months_between(start.replace(day=1), end)


def outstanding(ctype: ContributionType, today: date) -> dict:
    """Who still owes towards a mandatory type: active event participants, expected vs paid."""
    expected = expected_per_person(ctype, today)
    participants = (
        EventParticipant.objects.filter(
            event=ctype.event, status=EventParticipant.Status.ACTIVE, person__deleted_at__isnull=True
        )
        .select_related("person")
        .annotate(
            paid=Sum(
                "person__contributions__amount",
                filter=Q(
                    person__contributions__contribution_type=ctype,
                    person__contributions__status=Contribution.Status.CONFIRMED,
                ),
            )
        )
    )
    rows = []
    for p in participants:
        paid = p.paid or ZERO
        due = max(expected - paid, ZERO)
        rows.append(
            {
                "person": str(p.person_id),
                "person_name": p.person.full_name,
                "mobile": p.person.mobile,
                "expected": _money(expected),
                "paid": _money(paid),
                "due": _money(due),
            }
        )
    rows.sort(key=lambda r: (-Decimal(r["due"]), r["person_name"]))
    return {
        "expected_per_person": _money(expected),
        "participants": len(rows),
        "total_expected": _money(expected * len(rows)),
        "total_paid": _money(sum((Decimal(r["paid"]) for r in rows), ZERO)),
        "total_due": _money(sum((Decimal(r["due"]) for r in rows), ZERO)),
        "people_with_dues": sum(1 for r in rows if Decimal(r["due"]) > 0),
        "results": rows,
    }
