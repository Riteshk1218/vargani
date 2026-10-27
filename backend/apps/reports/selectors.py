"""Income, expenses and balance. The single place these numbers are computed, so the dashboard, reports and
exports always agree.

Income   = confirmed contribution lines + recorded other income
Expenses = approved expenses
Balance  = Income − Expenses
"""

from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth

from apps.contributions.models import Contribution
from apps.core.dates import filter_days
from apps.expenses.models import Expense, OtherIncome

ZERO = Decimal("0.00")


def money(value) -> str:
    return f"{(value or ZERO):.2f}"


def confirmed_lines(org, events, days=None):
    lines = Contribution.objects.for_org(org).filter(event__in=events, status=Contribution.Status.CONFIRMED)
    return _on_days(lines, "contributed_on", org, days)


def approved_expenses(org, events, days=None):
    expenses = Expense.objects.for_org(org).filter(event__in=events, status=Expense.Status.APPROVED)
    return _on_days(expenses, "expense_date", org, days)


def recorded_income(org, events, days=None):
    income = OtherIncome.objects.for_org(org).filter(event__in=events, status=OtherIncome.Status.RECORDED)
    return _on_days(income, "received_on", org, days)


def _on_days(qs, field, org, days):
    """`days` is an optional (date_from, date_to) pair; either end may be None."""
    if not days:
        return qs
    return filter_days(qs, field, org, *days)


def _total(qs) -> Decimal:
    return qs.aggregate(total=Sum("amount"))["total"] or ZERO


def finance_totals(org, events, days=None) -> dict:
    contributions = _total(confirmed_lines(org, events, days))
    other_income = _total(recorded_income(org, events, days))
    expenses = _total(approved_expenses(org, events, days))
    income = contributions + other_income
    return {
        "contributions": contributions,
        "other_income": other_income,
        "income": income,
        "expenses": expenses,
        "balance": income - expenses,
    }


def expenses_by_category(org, events, days=None):
    return list(
        approved_expenses(org, events, days)
        .values("category", "category__name")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")
    )


def expenses_by_month(org, events, days=None):
    return list(
        approved_expenses(org, events, days)
        .annotate(month=TruncMonth("expense_date"))
        .values("month")
        .annotate(total=Sum("amount"))
        .order_by("month")
    )


def income_by_source(org, events):
    return list(
        recorded_income(org, events)
        .values("source")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")
    )


def _by_event(qs, **filters):
    return {row["event"]: row["total"] for row in qs.filter(**filters).values("event").annotate(total=Sum("amount"))}


def event_summaries(org, events) -> list[dict]:
    """One row per event: Collection − Approved expenses = Balance, plus pending and rejected expenses.

    Each event belongs to one financial year of one organization (mandal), so the rows never mix years or
    events. Collection = confirmed contribution lines; other income is shown separately and counts in the
    balance, as everywhere else (finance_totals).
    """
    events = list(events.select_related("financial_year").order_by("-financial_year__start_date", "start_date", "name"))
    ids = [e.pk for e in events]
    collected = _by_event(Contribution.objects.for_org(org).filter(event__in=ids, status=Contribution.Status.CONFIRMED))
    income = _by_event(OtherIncome.objects.for_org(org).filter(event__in=ids, status=OtherIncome.Status.RECORDED))
    expenses = Expense.objects.for_org(org).filter(event__in=ids)
    approved = _by_event(expenses, status=Expense.Status.APPROVED)
    pending = _by_event(expenses, status=Expense.Status.SUBMITTED)
    rejected = _by_event(expenses, status=Expense.Status.REJECTED)
    rows = []
    for event in events:
        collection = collected.get(event.pk) or ZERO
        other = income.get(event.pk) or ZERO
        spent = approved.get(event.pk) or ZERO
        rows.append(
            {
                "event": {"id": str(event.pk), "name": event.name, "status": event.status},
                "financial_year": {"id": str(event.financial_year_id), "label": event.financial_year.label},
                "collection": money(collection),
                "other_income": money(other),
                "approved_expenses": money(spent),
                "pending_expenses": money(pending.get(event.pk)),
                "rejected_expenses": money(rejected.get(event.pk)),
                "balance": money(collection + other - spent),
            }
        )
    return rows
