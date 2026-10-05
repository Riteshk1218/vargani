"""Expense approval flow and other income. Every change is audited; nothing is ever deleted.

draft ──submit──▶ submitted ──approve──▶ approved ──void──▶ void
  ▲                   │ reject                         ▲
  └──── edit ──── rejected                 draft/submitted/rejected ──void──┘
"""

from datetime import timedelta

from django.db import transaction
from django.forms.models import model_to_dict
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError

from apps.audit import services as audit
from apps.core.exceptions import BusinessRuleViolation, InvalidStateTransition
from apps.events.models import Event
from apps.organizations.models import FinancialYear

from .models import Expense, OtherIncome

SUBMIT = "expense_submit"
APPROVE = "approve"
REJECT = "reject"
VOID = "void"
EDITABLE = {Expense.Status.DRAFT, Expense.Status.SUBMITTED, Expense.Status.REJECTED}
CLOSED_EVENT = {Event.Status.CLOSED, Event.Status.ARCHIVED}


def check_event_open(event):
    if event.status in CLOSED_EVENT or event.deleted_at is not None:
        raise BusinessRuleViolation(_("This event is closed. Money records cannot be added or changed."))
    if event.financial_year.status == FinancialYear.Status.CLOSED:
        raise BusinessRuleViolation(_("This financial year is closed."))


def check_not_future(day, field):
    if day > timezone.localdate() + timedelta(days=1):
        raise ValidationError({field: [_("The date cannot be in the future.")]})


def _snapshot(obj):
    return model_to_dict(obj)


def _audit(obj, action, *, request, actor, before=None):
    audit.record(
        request=request,
        actor=actor,
        organization=obj.organization,
        action=action,
        entity_type=obj._meta.label_lower,
        entity_id=obj.pk,
        before=before,
        after=_snapshot(obj),
    )


def _lock(expense):
    return Expense.objects.select_for_update().select_related("organization").get(pk=expense.pk)


def create_expense(*, org, data, request=None, actor=None) -> Expense:
    event = data["event"]
    check_event_open(event)
    check_not_future(data["expense_date"], "expense_date")
    with transaction.atomic():
        expense = Expense.objects.create(
            organization=org,
            financial_year_id=event.financial_year_id,
            created_by=actor,
            updated_by=actor,
            **data,
        )
        _audit(expense, audit.CREATE, request=request, actor=actor)
    return expense


def update_expense(expense, *, data, request=None, actor=None) -> Expense:
    with transaction.atomic():
        expense = _lock(expense)
        if expense.status not in EDITABLE:
            raise InvalidStateTransition()
        check_event_open(expense.event)
        if "expense_date" in data:
            check_not_future(data["expense_date"], "expense_date")
        before = _snapshot(expense)
        for field, value in data.items():
            setattr(expense, field, value)
        if expense.status == Expense.Status.REJECTED:
            expense.status = Expense.Status.DRAFT  # edited after rejection: submit again
        expense.updated_by = actor
        expense.save()
        _audit(expense, audit.UPDATE, request=request, actor=actor, before=before)
    return expense


def _approve_now(expense, actor, now):
    expense.status = Expense.Status.APPROVED
    expense.decided_by = actor
    expense.decided_at = now


def submit(expense, *, request=None, actor=None) -> Expense:
    """Send for approval. Organizations that switched off expense approval go straight to approved."""
    with transaction.atomic():
        expense = _lock(expense)
        if expense.status not in (Expense.Status.DRAFT, Expense.Status.REJECTED):
            raise InvalidStateTransition()
        check_event_open(expense.event)
        before = _snapshot(expense)
        now = timezone.now()
        expense.status = Expense.Status.SUBMITTED
        expense.submitted_by = actor
        expense.submitted_at = now
        expense.rejection_reason = ""
        if not expense.organization.settings.get("require_expense_approval", True):
            _approve_now(expense, actor, now)
        expense.updated_by = actor
        expense.save()
        _audit(expense, SUBMIT, request=request, actor=actor, before=before)
    return expense


def approve(expense, *, approver_membership, request=None, actor=None) -> Expense:
    # Four-eyes rule, as for receipt voids: someone else approves, except an Organization Admin.
    if expense.submitted_by_id == actor.pk and approver_membership.role.code != "org_admin":
        raise BusinessRuleViolation(_("Someone other than the requester must approve this."))
    with transaction.atomic():
        expense = _lock(expense)
        if expense.status != Expense.Status.SUBMITTED:
            raise InvalidStateTransition()
        check_event_open(expense.event)
        before = _snapshot(expense)
        _approve_now(expense, actor, timezone.now())
        expense.updated_by = actor
        expense.save()
        _audit(expense, APPROVE, request=request, actor=actor, before=before)
    return expense


def reject(expense, *, reason, request=None, actor=None) -> Expense:
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError({"reason": [_("Give a reason.")]})
    with transaction.atomic():
        expense = _lock(expense)
        if expense.status != Expense.Status.SUBMITTED:
            raise InvalidStateTransition()
        before = _snapshot(expense)
        expense.status = Expense.Status.REJECTED
        expense.rejection_reason = reason
        expense.decided_by = actor
        expense.decided_at = timezone.now()
        expense.updated_by = actor
        expense.save()
        _audit(expense, REJECT, request=request, actor=actor, before=before)
    return expense


def void_expense(expense, *, reason, can_approve, request=None, actor=None) -> Expense:
    """Cancel an expense. An approved expense needs approval rights, because it changes the balance."""
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError({"reason": [_("Give a reason.")]})
    with transaction.atomic():
        expense = _lock(expense)
        if expense.status == Expense.Status.VOID:
            raise InvalidStateTransition()
        if expense.status == Expense.Status.APPROVED and not can_approve:
            raise BusinessRuleViolation(_("Only an approver can void an approved expense."))
        before = _snapshot(expense)
        expense.status = Expense.Status.VOID
        expense.void_reason = reason
        expense.voided_by = actor
        expense.voided_at = timezone.now()
        expense.updated_by = actor
        expense.save()
        _audit(expense, VOID, request=request, actor=actor, before=before)
    return expense


def record_income(*, org, data, request=None, actor=None) -> OtherIncome:
    event = data["event"]
    check_event_open(event)
    check_not_future(data["received_on"], "received_on")
    fund = data.get("fund")
    if fund is not None and fund.event_id != event.pk:
        raise ValidationError({"fund": [_("This fund belongs to another event.")]})
    with transaction.atomic():
        income = OtherIncome.objects.create(
            organization=org, financial_year_id=event.financial_year_id, created_by=actor, updated_by=actor, **data
        )
        _audit(income, audit.CREATE, request=request, actor=actor)
    return income


def void_income(income, *, reason, request=None, actor=None) -> OtherIncome:
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError({"reason": [_("Give a reason.")]})
    with transaction.atomic():
        income = OtherIncome.objects.select_for_update().get(pk=income.pk)
        if income.status == OtherIncome.Status.VOID:
            raise InvalidStateTransition()
        before = _snapshot(income)
        income.status = OtherIncome.Status.VOID
        income.void_reason = reason
        income.voided_by = actor
        income.voided_at = timezone.now()
        income.updated_by = actor
        income.save()
        _audit(income, VOID, request=request, actor=actor, before=before)
    return income
