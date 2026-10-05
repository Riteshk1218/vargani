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
from apps.expenses.models import Expense, OtherIncome

ZERO = Decimal("0.00")


def money(value) -> str:
    return f"{(value or ZERO):.2f}"


def confirmed_lines(org, events):
    return Contribution.objects.for_org(org).filter(event__in=events, status=Contribution.Status.CONFIRMED)


def approved_expenses(org, events):
    return Expense.objects.for_org(org).filter(event__in=events, status=Expense.Status.APPROVED)


def recorded_income(org, events):
    return OtherIncome.objects.for_org(org).filter(event__in=events, status=OtherIncome.Status.RECORDED)


def _total(qs) -> Decimal:
    return qs.aggregate(total=Sum("amount"))["total"] or ZERO


def finance_totals(org, events) -> dict:
    contributions = _total(confirmed_lines(org, events))
    other_income = _total(recorded_income(org, events))
    expenses = _total(approved_expenses(org, events))
    income = contributions + other_income
    return {
        "contributions": contributions,
        "other_income": other_income,
        "income": income,
        "expenses": expenses,
        "balance": income - expenses,
    }


def expenses_by_category(org, events):
    return list(
        approved_expenses(org, events)
        .values("category", "category__name")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")
    )


def expenses_by_month(org, events):
    return list(
        approved_expenses(org, events)
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
