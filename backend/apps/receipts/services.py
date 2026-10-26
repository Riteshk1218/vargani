"""Receipt numbering and snapshots.

Numbers are gapless and unique per series: the series row is locked with SELECT ... FOR UPDATE inside the
transaction that confirms the payment, so concurrent collectors queue on the lock, and a rollback also rolls
back the counter. The unique constraints on receipts are the final safety net.
"""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.audit import services as audit
from apps.notifications import hooks as notify
from apps.organizations import form_studio

from .models import Receipt, ReceiptSeries

RECEIPT_ISSUE = "receipt_issue"


def series_for(event) -> ReceiptSeries:
    year_label = str(event.financial_year.start_date.year)
    series, _ = ReceiptSeries.objects.get_or_create(
        organization_id=event.organization_id,
        prefix=event.code,
        year_label=year_label,
        defaults={"event": event},
    )
    return series


def _money(value) -> str:
    return f"{value:.2f}"


def build_snapshot(payment) -> dict:
    """Everything a receipt shows, frozen at issue time. Later edits to org/person/event never change it."""
    org = payment.organization
    person = payment.payer
    event = payment.event
    collector = payment.collector
    lines = []
    for line in payment.lines.select_related("contribution_type", "fund").order_by("period_month", "created_at"):
        lines.append(
            {
                "contribution_type": line.contribution_type.name,
                "fund": line.fund.name if line.fund else None,
                "period_month": line.period_month.isoformat() if line.period_month else None,
                "amount": _money(line.amount),
                "towards_balance": line.due_id is not None,
            }
        )
    # What this person still owes after this receipt: balances kept now, and older ones still open.
    from apps.contributions.models import Due
    from apps.contributions.selectors import with_balance

    balance = []
    if person is not None:
        open_dues = with_balance(
            Due.objects.filter(person=person, event=event, status=Due.Status.OPEN).select_related("contribution_type")
        ).order_by("period_month", "created_at")
        for due in open_dues:
            if due.remaining > 0:
                balance.append(
                    {
                        "contribution_type": due.contribution_type.name,
                        "period_month": due.period_month.isoformat() if due.period_month else None,
                        "amount": _money(due.remaining),
                    }
                )
    address = ", ".join(
        part for part in [org.address_line1, org.address_line2, org.city, org.district, org.state, org.pincode] if part
    )
    if person is not None:
        person_address = ", ".join(
            part for part in [person.unit, person.building, person.area, person.address_line, person.city] if part
        )
        payer = {"name": person.full_name, "mobile": person.mobile, "address": person_address}
    else:
        payer = {"name": payment.payer_name, "mobile": "", "address": "", "anonymous": True}
    return {
        "organization": {
            "name": org.name,
            "address": address,
            "phone": org.phone,
            "email": org.email,
            "registration_type": org.registration_type,
            "registration_number": org.registration_number,
            "logo": org.logo or None,
        },
        "person": payer,
        "event": {"name": event.name, "code": event.code},
        "financial_year": payment.financial_year.label,
        "lines": lines,
        "total": _money(payment.amount),
        "balance_lines": balance,
        "balance_total": _money(sum((Decimal(b["amount"]) for b in balance), Decimal("0"))),
        "currency": org.currency,
        "mode": payment.mode,
        "mode_label": form_studio.mode_label(org, payment.mode),
        "custom_fields": [
            {"label": f["label"], "value": f["value"]} for f in form_studio.describe_values(org, payment.custom_fields)
        ],
        "reference_number": payment.reference_number,
        "cheque_bank": payment.cheque_bank,
        "cheque_date": payment.cheque_date.isoformat() if payment.cheque_date else None,
        "paid_at": payment.paid_at.isoformat(),
        "timezone": org.timezone,
        "collector": collector.user.full_name if collector else None,
        "thank_you_message": event.thank_you_message,
    }


def issue_receipt(payment, *, request=None, actor=None, replaces=None) -> Receipt:
    """Issue the receipt for a successful payment. Must run inside the payment's transaction."""
    assert transaction.get_connection().in_atomic_block, "issue_receipt must run inside a transaction"
    series = series_for(payment.event)
    series = ReceiptSeries.objects.select_for_update().get(pk=series.pk)
    number = series.next_number
    series.next_number = number + 1
    series.save(update_fields=["next_number", "updated_at"])

    receipt = Receipt.objects.create(
        organization_id=payment.organization_id,
        financial_year_id=payment.financial_year_id,
        event_id=payment.event_id,
        payment=payment,
        series=series,
        sequence=number,
        receipt_number=series.format(number),
        issued_at=timezone.now(),
        language=payment.organization.receipt_language or "en",
        snapshot=build_snapshot(payment),
        replaces_receipt=replaces,
        created_by=actor,
        updated_by=actor,
    )
    audit.record(
        request=request,
        actor=actor,
        organization=payment.organization,
        action=RECEIPT_ISSUE,
        entity_type="receipts.receipt",
        entity_id=receipt.pk,
        after={
            "receipt_number": receipt.receipt_number,
            "payment": str(payment.pk),
            "total": str(payment.amount),
            "replaces": replaces.receipt_number if replaces else None,
        },
    )
    notify.receipt_issued(receipt, actor)
    return receipt
