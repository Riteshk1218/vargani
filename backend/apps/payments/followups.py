"""Door-to-door follow-ups: one pavti (receipt) per house, updated on every later visit.

A pavti may be given before all of the money came: what is missing is kept as balances (`Due`) on that
payment, with a follow-up date for the next visit. On a later visit the collectors open the same pavti and
either record the money that came now (it is added to the same pavti, which keeps its number) or move the
follow-up date. No new pavti is made. A pavti is overdue when its follow-up date has passed and money is
still owed on it.
"""

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, DecimalField, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError

from apps.audit import services as audit
from apps.contributions.models import Contribution, Due
from apps.contributions.selectors import due_remaining
from apps.core.admin_override import allow_admin_changes
from apps.core.exceptions import BusinessRuleViolation, InvalidStateTransition
from apps.events.models import Event
from apps.organizations.models import FinancialYear
from apps.receipts.models import Receipt
from apps.receipts.services import build_snapshot

from .models import Payment, PaymentMode
from .services import REFERENCE_REQUIRED, _org_today

PAVTI_VISIT = "pavti_visit"

UNPAID = "unpaid"
PARTLY_PAID = "partly_paid"
PAID = "paid"

OVERDUE = "overdue"
TODAY = "today"
UPCOMING = "upcoming"


def _sum_subquery(queryset, group_by):
    total = queryset.order_by().values(group_by).annotate(total=Sum("amount")).values("total")[:1]
    return Coalesce(Subquery(total), Value(Decimal("0")), output_field=DecimalField(max_digits=12, decimal_places=2))


def with_pavti_balance(queryset):
    """Payments with `balance_due`: what is still owed on the balances kept on that pavti."""
    kept = _sum_subquery(Due.objects.filter(payment=OuterRef("pk"), status=Due.Status.OPEN), "payment")
    settled = _sum_subquery(
        Contribution.objects.filter(
            due__payment=OuterRef("pk"), due__status=Due.Status.OPEN, status=Contribution.Status.CONFIRMED
        ),
        "due__payment",
    )
    return queryset.annotate(balance_due=kept - settled)


def org_today(org) -> date:
    return _org_today(org, timezone.now())


def owing(queryset):
    """Received pavtis that still have money owed on them (needs `with_pavti_balance`)."""
    return queryset.filter(status=Payment.Status.SUCCESSFUL, balance_due__gt=0)


def filter_pavti(queryset, value):
    if value == UNPAID:
        return owing(queryset).filter(amount=0)
    if value == PARTLY_PAID:
        return owing(queryset).filter(amount__gt=0)
    if value == "owing":
        return owing(queryset)
    if value == PAID:
        return queryset.filter(status=Payment.Status.SUCCESSFUL, balance_due__lte=0)
    return queryset


def filter_follow_up(queryset, value, today: date):
    if value == OVERDUE:
        return owing(queryset).filter(follow_up_on__lt=today)
    if value == TODAY:
        return owing(queryset).filter(follow_up_on=today)
    if value == UPCOMING:
        return owing(queryset).filter(follow_up_on__gt=today)
    if value == "none":
        return owing(queryset).filter(follow_up_on__isnull=True)
    return queryset


def counts(queryset, today: date) -> dict:
    """Dashboard numbers: pavtis to visit (needs `with_pavti_balance`)."""
    data = owing(queryset).aggregate(
        overdue=Count("id", filter=Q(follow_up_on__lt=today)),
        due_today=Count("id", filter=Q(follow_up_on=today)),
        owing=Count("id"),
        balance=Sum("balance_due"),
    )
    data["balance"] = f"{(data['balance'] or Decimal('0')):.2f}"
    data["paid"] = queryset.filter(status=Payment.Status.SUCCESSFUL, balance_due__lte=0).count()
    return data


def pavti_status(payment) -> str | None:
    if payment.status != Payment.Status.SUCCESSFUL:
        return None
    balance = getattr(payment, "balance_due", None) or Decimal("0")
    if balance <= 0:
        return PAID
    return UNPAID if payment.amount == 0 else PARTLY_PAID


def follow_up_state(payment, today: date) -> str | None:
    if pavti_status(payment) in (None, PAID) or payment.follow_up_on is None:
        return None
    if payment.follow_up_on < today:
        return OVERDUE
    if payment.follow_up_on == today:
        return TODAY
    return UPCOMING


def record_visit(
    payment,
    *,
    received=Decimal("0"),
    mode=None,
    reference_number="",
    follow_up_on=None,
    collector=None,
    request=None,
    actor=None,
) -> Payment:
    """A later visit to a house: add the money that came now to the same pavti and set the next follow-up date.

    `received` may be zero (nobody paid, only the date moves). When nothing is owed any more the follow-up
    date is cleared. The pavti keeps its number; its printout shows the new total and what is still owed.
    """
    received = Decimal(received or 0)
    reference_number = (reference_number or "").strip()
    with transaction.atomic():
        payment = Payment.objects.select_for_update().select_related("organization", "event").get(pk=payment.pk)
        org = payment.organization
        if payment.status != Payment.Status.SUCCESSFUL:
            raise InvalidStateTransition()
        if payment.event.status != Event.Status.ACTIVE:
            raise BusinessRuleViolation(_("This event is not active. New collections are not allowed."))
        if FinancialYear.objects.filter(pk=payment.financial_year_id, status=FinancialYear.Status.CLOSED).exists():
            raise BusinessRuleViolation(_("This financial year is closed."))
        dues = list(
            Due.objects.select_for_update()
            .filter(payment=payment, status=Due.Status.OPEN)
            .select_related("contribution_type")
            .order_by("created_at")
        )
        owed_by_due = [(due, due_remaining(due)) for due in dues]
        owed = sum((left for _due, left in owed_by_due), Decimal("0"))
        if owed <= 0:
            raise ValidationError({"received": [_("Nothing is owed on this pavti.")]})
        if received < 0 or received > owed:
            raise ValidationError({"received": [_("This is more than the balance still owed.")]})
        today = _org_today(org, timezone.now())
        if follow_up_on is not None and follow_up_on < today and received < owed:
            raise ValidationError({"follow_up_on": [_("The follow-up date cannot be in the past.")]})
        before = {
            "amount": str(payment.amount),
            "mode": payment.mode,
            "follow_up_on": payment.follow_up_on.isoformat() if payment.follow_up_on else None,
            "balance_due": str(owed),
        }

        if received > 0:
            mode = mode or payment.mode
            if mode not in PaymentMode.values or mode == PaymentMode.ONLINE:
                raise ValidationError({"mode": [_("This payment mode cannot be recorded manually.")]})
            if mode in REFERENCE_REQUIRED and not reference_number:
                raise ValidationError({"reference_number": [_("Enter the cheque or transaction number.")]})
            # The pavti's amount grows, which the money triggers allow only with the admin override; the
            # change is limited to settling what this pavti already shows as owed, and is audited below.
            allow_admin_changes()
            first_money = payment.amount == 0
            note = "" if first_money or mode == payment.mode else " ".join(filter(None, [mode, reference_number]))
            left = received
            lines = []
            for due, still in owed_by_due:
                now = min(still, left)
                left -= now
                if now <= 0:
                    continue
                lines.append(
                    Contribution(
                        organization=org,
                        financial_year_id=payment.financial_year_id,
                        event_id=payment.event_id,
                        fund_id=due.contribution_type.fund_id,
                        contribution_type_id=due.contribution_type_id,
                        person_id=due.person_id,
                        payment=payment,
                        period_month=due.period_month,
                        amount=now,
                        contributed_on=today,
                        status=Contribution.Status.CONFIRMED,
                        collector=collector,
                        notes=note,
                        due=due,
                        created_by=actor,
                        updated_by=actor,
                    )
                )
            Contribution.objects.bulk_create(lines)
            payment.amount += received
            if first_money:
                payment.mode = mode
                payment.reference_number = reference_number
        payment.follow_up_on = None if received >= owed else follow_up_on
        payment.updated_by = actor
        payment.save(update_fields=["amount", "mode", "reference_number", "follow_up_on", "updated_by", "updated_at"])

        if received > 0:
            receipt = payment.receipts.filter(status=Receipt.Status.ISSUED).first()
            if receipt is not None:
                receipt.snapshot = build_snapshot(payment)
                receipt.updated_by = actor
                receipt.save(update_fields=["snapshot", "updated_by", "updated_at"])

        audit.record(
            request=request,
            actor=actor,
            organization=org,
            action=PAVTI_VISIT,
            entity_type="payments.payment",
            entity_id=payment.pk,
            before=before,
            after={
                "amount": str(payment.amount),
                "mode": payment.mode,
                "received": str(received),
                "follow_up_on": payment.follow_up_on.isoformat() if payment.follow_up_on else None,
                "balance_due": str(owed - received),
            },
        )
    return payment
