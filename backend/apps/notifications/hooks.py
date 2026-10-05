"""Who hears about what. Called from the services that make the change, inside the same transaction."""

from .services import members_with_permission, money, notify


def _name(user):
    return user.full_name if user else ""


def expense_submitted(expense, actor):
    approvers = members_with_permission(expense.organization, "expenses.approve", exclude=actor)
    notify(
        approvers,
        "expense_submitted",
        {"actor": _name(actor), "amount": money(expense.amount), "payee": expense.payee},
        organization=expense.organization,
        entity=expense,
        link="/app/expenses",
    )


def expense_decided(expense, actor, approved: bool):
    if expense.submitted_by_id is None or expense.submitted_by_id == actor.pk:
        return
    notify(
        [expense.submitted_by],
        "expense_approved" if approved else "expense_rejected",
        {
            "actor": _name(actor),
            "amount": money(expense.amount),
            "payee": expense.payee,
            "reason": expense.rejection_reason,
        },
        organization=expense.organization,
        entity=expense,
        link="/app/expenses",
    )


def void_requested(void_request, receipt, actor):
    approvers = members_with_permission(receipt.organization, "receipts.void_approve", exclude=actor)
    notify(
        approvers,
        "void_requested",
        {
            "actor": _name(actor),
            "number": receipt.receipt_number,
            "amount": money(receipt.payment.amount),
            "reason": void_request.reason,
        },
        organization=receipt.organization,
        entity=receipt,
        link="/app/approvals",
    )


def void_decided(void_request, receipt, actor, approved: bool):
    if void_request.requested_by_id is None or void_request.requested_by_id == actor.pk:
        return
    notify(
        [void_request.requested_by],
        "void_approved" if approved else "void_rejected",
        {"actor": _name(actor), "number": receipt.receipt_number},
        organization=receipt.organization,
        entity=receipt,
        link=f"/app/receipts/{receipt.pk}",
    )


def receipt_issued(receipt, actor):
    """Tell the contributor, when they have a portal login and the organization has the portal switched on."""
    org = receipt.organization
    payer = receipt.payment.payer
    if not org.settings.get("member_portal_enabled") or payer.user_id is None:
        return
    if actor is not None and payer.user_id == actor.pk:
        return
    notify(
        [payer.user],
        "receipt_issued",
        {"amount": money(receipt.payment.amount), "event": receipt.event.name, "number": receipt.receipt_number},
        organization=org,
        entity=receipt,
        link=f"/portal/receipts/{receipt.pk}",
    )
