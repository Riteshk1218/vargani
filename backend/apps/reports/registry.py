"""Every report, as data: a title, columns and rows. The JSON endpoint, CSV, Excel and PDF all render the
same structure, so a number never differs between screen and file.

Each report function receives a ReportContext (organization, resolved events, parsed filters, and the
caller's permission context) and returns a Report. Labels are translated at call time, so the caller's
language (or the export job's language) applies.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_noop

from apps.audit.models import AuditLog
from apps.contributions.models import ContributionType
from apps.contributions.selectors import outstanding
from apps.events.models import Event
from apps.expenses.models import Expense
from apps.funds.models import Fund
from apps.payments.models import Payment
from apps.people.models import Person
from apps.receipts.models import Receipt
from apps.receipts.rendering import MODE_LABELS

from . import selectors as sel

GENERAL, FINANCIAL, AUDIT = "general", "financial", "audit"
MAX_ROWS = 50_000

SOURCE_LABELS = {
    "donation_box": gettext_noop("Donation box"),
    "sponsorship": gettext_noop("Sponsorship"),
    "interest": gettext_noop("Bank interest"),
    "sale": gettext_noop("Sales"),
    "other": gettext_noop("Other"),
}
STATUS_LABELS = {
    "draft": gettext_noop("Draft"),
    "submitted": gettext_noop("Submitted"),
    "approved": gettext_noop("Approved"),
    "rejected": gettext_noop("Rejected"),
    "void": gettext_noop("Void"),
    "issued": gettext_noop("Issued"),
    "recorded": gettext_noop("Recorded"),
    "active": gettext_noop("Active"),
    "closed": gettext_noop("Closed"),
    "archived": gettext_noop("Archived"),
}


def mode_label(mode):
    return _(MODE_LABELS.get(mode, mode)) if mode else ""


def status_label(status):
    return _(STATUS_LABELS.get(status, status)) if status else ""


@dataclass
class Column:
    key: str
    label: str
    kind: str = "text"  # text | money | number | date | datetime


@dataclass
class Report:
    title: str
    columns: list[Column]
    rows: list[dict]
    totals: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


@dataclass
class ReportContext:
    org: object
    events: object  # queryset of events the report covers
    event: Event | None
    filters: dict
    org_context: object
    scope_label: str = ""

    def date_range(self, qs, field_name):
        if self.filters.get("date_from"):
            qs = qs.filter(**{f"{field_name}__gte": self.filters["date_from"]})
        if self.filters.get("date_to"):
            qs = qs.filter(**{f"{field_name}__lte": self.filters["date_to"]})
        return qs


def _month(value):
    return value.strftime("%Y-%m") if value else ""


# --- general -------------------------------------------------------------------------------------------------
def people(ctx: ReportContext) -> Report:
    qs = Person.objects.for_org(ctx.org).alive().order_by("full_name")
    if ctx.event is not None:
        qs = qs.filter(event_participations__event=ctx.event).distinct()
    rows = [
        {
            "name": p.full_name,
            "mobile": p.mobile,
            "email": p.email,
            "unit": p.unit,
            "building": p.building,
            "area": p.area,
            "city": p.city,
            "status": status_label("active") if p.is_active else _("Inactive"),
        }
        for p in qs[:MAX_ROWS]
    ]
    return Report(
        _("People"),
        [
            Column("name", _("Name")),
            Column("mobile", _("Mobile")),
            Column("email", _("Email")),
            Column("unit", _("Flat / house")),
            Column("building", _("Building")),
            Column("area", _("Area")),
            Column("city", _("City")),
            Column("status", _("Status")),
        ],
        rows,
        {"count": len(rows)},
    )


def events(ctx: ReportContext) -> Report:
    qs = ctx.events.annotate(people=Count("participants", distinct=True)).order_by("start_date", "name")
    rows = [
        {
            "name": e.name,
            "code": e.code,
            "status": status_label(e.status),
            "start_date": e.start_date,
            "end_date": e.end_date,
            "participants": e.people,
            "target": e.target_amount,
        }
        for e in qs
    ]
    return Report(
        _("Events"),
        [
            Column("name", _("Event")),
            Column("code", _("Code")),
            Column("status", _("Status")),
            Column("start_date", _("Starts"), "date"),
            Column("end_date", _("Ends"), "date"),
            Column("participants", _("Participants"), "number"),
            Column("target", _("Target"), "money"),
        ],
        rows,
    )


# --- financial -----------------------------------------------------------------------------------------------
def _lines(ctx):
    qs = ctx.date_range(sel.confirmed_lines(ctx.org, ctx.events), "contributed_on")
    f = ctx.filters
    for key in ("fund", "contribution_type", "person", "collector"):
        if f.get(key):
            qs = qs.filter(**{key: f[key]})
    if f.get("mode"):
        qs = qs.filter(payment__mode=f["mode"])
    return qs


def contributions(ctx: ReportContext) -> Report:
    qs = _lines(ctx).select_related("person", "contribution_type", "fund", "payment", "collector__user")
    qs = qs.prefetch_related("payment__receipts").order_by("contributed_on", "created_at")
    rows = []
    for c in qs[:MAX_ROWS]:
        receipt = next((r.receipt_number for r in c.payment.receipts.all() if r.status == "issued"), "")
        rows.append(
            {
                "date": c.contributed_on,
                "person": c.person.full_name,
                "mobile": c.person.mobile,
                "type": c.contribution_type.name,
                "month": _month(c.period_month),
                "fund": c.fund.name if c.fund else "",
                "mode": mode_label(c.payment.mode),
                "receipt": receipt,
                "collector": c.collector.user.full_name if c.collector else "",
                "amount": c.amount,
            }
        )
    return Report(
        _("Contributions"),
        [
            Column("date", _("Date"), "date"),
            Column("person", _("Name")),
            Column("mobile", _("Mobile")),
            Column("type", _("Contribution type")),
            Column("month", _("For month")),
            Column("fund", _("Fund")),
            Column("mode", _("Payment mode")),
            Column("receipt", _("Receipt no.")),
            Column("collector", _("Collected by")),
            Column("amount", _("Amount"), "money"),
        ],
        rows,
        {"amount": sum((r["amount"] for r in rows), Decimal(0)), "count": len(rows)},
    )


def monthly_collection(ctx: ReportContext) -> Report:
    qs = (
        _lines(ctx)
        .annotate(month=TruncMonth("contributed_on"))
        .values("month")
        .annotate(total=Sum("amount"), people=Count("person", distinct=True), payments=Count("payment", distinct=True))
        .order_by("month")
    )
    rows = [
        {"month": _month(r["month"]), "payments": r["payments"], "people": r["people"], "amount": r["total"]}
        for r in qs
    ]
    return Report(
        _("Monthly collection"),
        [
            Column("month", _("Month")),
            Column("payments", _("Payments"), "number"),
            Column("people", _("Contributors"), "number"),
            Column("amount", _("Amount"), "money"),
        ],
        rows,
        {"amount": sum((r["amount"] for r in rows), Decimal(0))},
    )


def fund_wise(ctx: ReportContext) -> Report:
    lines = dict(_lines(ctx).values("fund").annotate(total=Sum("amount")).values_list("fund", "total"))
    income = dict(
        ctx.date_range(sel.recorded_income(ctx.org, ctx.events), "received_on")
        .values("fund")
        .annotate(total=Sum("amount"))
        .values_list("fund", "total")
    )
    rows = []
    for fund in Fund.objects.for_org(ctx.org).filter(event__in=ctx.events).select_related("event").order_by("name"):
        c, o = lines.get(fund.pk) or Decimal(0), income.get(fund.pk) or Decimal(0)
        rows.append(
            {
                "fund": fund.name,
                "event": fund.event.name,
                "target": fund.target_amount,
                "contributions": c,
                "other_income": o,
                "total": c + o,
            }
        )
    c, o = lines.get(None) or Decimal(0), income.get(None) or Decimal(0)
    if c or o:
        rows.append(
            {"fund": _("No fund"), "event": "", "target": None, "contributions": c, "other_income": o, "total": c + o}
        )
    return Report(
        _("Fund-wise collection"),
        [
            Column("fund", _("Fund")),
            Column("event", _("Event")),
            Column("target", _("Target"), "money"),
            Column("contributions", _("Contributions"), "money"),
            Column("other_income", _("Other income"), "money"),
            Column("total", _("Total"), "money"),
        ],
        rows,
        {k: sum((r[k] for r in rows), Decimal(0)) for k in ("contributions", "other_income", "total")},
    )


def _payments(ctx):
    qs = Payment.objects.for_org(ctx.org).filter(event__in=ctx.events, status=Payment.Status.SUCCESSFUL)
    qs = ctx.date_range(qs, "paid_at__date")
    for key in ("person", "collector", "mode"):
        if ctx.filters.get(key):
            qs = qs.filter(**{"payer" if key == "person" else key: ctx.filters[key]})
    return qs


def payment_mode(ctx: ReportContext) -> Report:
    qs = _payments(ctx).values("mode").annotate(total=Sum("amount"), count=Count("id")).order_by("-total")
    rows = [{"mode": mode_label(r["mode"]), "payments": r["count"], "amount": r["total"]} for r in qs]
    return Report(
        _("Payment mode summary"),
        [
            Column("mode", _("Payment mode")),
            Column("payments", _("Payments"), "number"),
            Column("amount", _("Amount"), "money"),
        ],
        rows,
        {"payments": sum(r["payments"] for r in rows), "amount": sum((r["amount"] for r in rows), Decimal(0))},
    )


def collector_wise(ctx: ReportContext) -> Report:
    qs = (
        _payments(ctx)
        .values("collector", "collector__user__full_name")
        .annotate(total=Sum("amount"), count=Count("id"), people=Count("payer", distinct=True))
        .order_by("-total")
    )
    rows = [
        {
            "collector": r["collector__user__full_name"] or _("Office (no collector)"),
            "payments": r["count"],
            "people": r["people"],
            "amount": r["total"],
        }
        for r in qs
    ]
    return Report(
        _("Collector-wise collection"),
        [
            Column("collector", _("Collector")),
            Column("payments", _("Payments"), "number"),
            Column("people", _("Contributors"), "number"),
            Column("amount", _("Amount"), "money"),
        ],
        rows,
        {"payments": sum(r["payments"] for r in rows), "amount": sum((r["amount"] for r in rows), Decimal(0))},
    )


def receipts(ctx: ReportContext) -> Report:
    qs = Receipt.objects.for_org(ctx.org).filter(event__in=ctx.events)
    qs = ctx.date_range(qs, "issued_at__date")
    if ctx.filters.get("status"):
        qs = qs.filter(status=ctx.filters["status"])
    qs = qs.select_related("payment__payer", "payment__collector__user").order_by("series_id", "sequence")
    rows = [
        {
            "number": r.receipt_number,
            "date": timezone.localtime(r.issued_at).date(),
            "person": r.payment.payer.full_name,
            "mode": mode_label(r.payment.mode),
            "collector": r.payment.collector.user.full_name if r.payment.collector else "",
            "status": status_label(r.status),
            "void_reason": r.void_reason,
            "amount": r.payment.amount,
        }
        for r in qs[:MAX_ROWS]
    ]
    issued = qs.filter(status=Receipt.Status.ISSUED).aggregate(total=Sum("payment__amount"))["total"] or Decimal(0)
    return Report(
        _("Receipt register"),
        [
            Column("number", _("Receipt no.")),
            Column("date", _("Date"), "date"),
            Column("person", _("Name")),
            Column("mode", _("Payment mode")),
            Column("collector", _("Collected by")),
            Column("status", _("Status")),
            Column("void_reason", _("Void reason")),
            Column("amount", _("Amount"), "money"),
        ],
        rows,
        {"amount": issued, "count": len(rows)},
        [_("The total counts issued receipts only; void receipts are listed but not added.")],
    )


def dues(ctx: ReportContext) -> Report:
    types = ContributionType.objects.for_org(ctx.org).filter(event__in=ctx.events, is_mandatory=True, is_active=True)
    if ctx.filters.get("contribution_type"):
        types = types.filter(pk=ctx.filters["contribution_type"])
    today = timezone.localdate()
    rows = []
    for ctype in types.select_related("event"):
        for r in outstanding(ctype, today)["results"]:
            rows.append(
                {
                    "person": r["person_name"],
                    "mobile": r["mobile"],
                    "type": ctype.name,
                    "expected": Decimal(r["expected"]),
                    "paid": Decimal(r["paid"]),
                    "due": Decimal(r["due"]),
                }
            )
    rows.sort(key=lambda r: (-r["due"], r["person"]))
    return Report(
        _("Pending dues"),
        [
            Column("person", _("Name")),
            Column("mobile", _("Mobile")),
            Column("type", _("Contribution type")),
            Column("expected", _("Expected"), "money"),
            Column("paid", _("Paid"), "money"),
            Column("due", _("Due"), "money"),
        ],
        rows,
        {k: sum((r[k] for r in rows), Decimal(0)) for k in ("expected", "paid", "due")},
        [_("Only mandatory contribution types with an expected amount are included.")],
    )


def expenses(ctx: ReportContext) -> Report:
    status = ctx.filters.get("status") or Expense.Status.APPROVED
    qs = Expense.objects.for_org(ctx.org).filter(event__in=ctx.events)
    if status != "all":
        qs = qs.filter(status=status)
    qs = ctx.date_range(qs, "expense_date")
    if ctx.filters.get("category"):
        qs = qs.filter(category=ctx.filters["category"])
    if ctx.filters.get("mode"):
        qs = qs.filter(mode=ctx.filters["mode"])
    qs = qs.select_related("category", "decided_by").order_by("expense_date", "created_at")
    rows = [
        {
            "date": e.expense_date,
            "category": e.category.name,
            "payee": e.payee,
            "description": e.description,
            "mode": mode_label(e.mode),
            "reference": e.reference_number,
            "status": status_label(e.status),
            "approved_by": e.decided_by.full_name if e.decided_by and e.status == "approved" else "",
            "amount": e.amount,
        }
        for e in qs[:MAX_ROWS]
    ]
    return Report(
        _("Expenses"),
        [
            Column("date", _("Date"), "date"),
            Column("category", _("Category")),
            Column("payee", _("Paid to")),
            Column("description", _("Description")),
            Column("mode", _("Payment mode")),
            Column("reference", _("Reference")),
            Column("status", _("Status")),
            Column("approved_by", _("Approved by")),
            Column("amount", _("Amount"), "money"),
        ],
        rows,
        {"amount": sum((r["amount"] for r in rows), Decimal(0)), "count": len(rows)},
    )


def other_income(ctx: ReportContext) -> Report:
    qs = ctx.date_range(sel.recorded_income(ctx.org, ctx.events), "received_on")
    if ctx.filters.get("fund"):
        qs = qs.filter(fund=ctx.filters["fund"])
    rows = [
        {
            "date": i.received_on,
            "source": _(SOURCE_LABELS.get(i.source, i.source)),
            "fund": i.fund.name if i.fund else "",
            "mode": mode_label(i.mode),
            "reference": i.reference_number,
            "description": i.description,
            "amount": i.amount,
        }
        for i in qs.select_related("fund").order_by("received_on", "created_at")[:MAX_ROWS]
    ]
    return Report(
        _("Other income"),
        [
            Column("date", _("Date"), "date"),
            Column("source", _("Source")),
            Column("fund", _("Fund")),
            Column("mode", _("Payment mode")),
            Column("reference", _("Reference")),
            Column("description", _("Description")),
            Column("amount", _("Amount"), "money"),
        ],
        rows,
        {"amount": sum((r["amount"] for r in rows), Decimal(0))},
    )


def income_expense(ctx: ReportContext) -> Report:
    lines = ctx.date_range(sel.confirmed_lines(ctx.org, ctx.events), "contributed_on")
    income = ctx.date_range(sel.recorded_income(ctx.org, ctx.events), "received_on")
    spent = ctx.date_range(sel.approved_expenses(ctx.org, ctx.events), "expense_date")
    rows = []
    income_label, expense_label = _("Income"), _("Expense")
    for r in lines.values("contribution_type__name").annotate(total=Sum("amount")).order_by("-total"):
        rows.append(
            {"section": income_label, "head": r["contribution_type__name"], "income": r["total"], "expense": None}
        )
    for r in income.values("source").annotate(total=Sum("amount")).order_by("-total"):
        rows.append(
            {
                "section": income_label,
                "head": _(SOURCE_LABELS.get(r["source"], r["source"])),
                "income": r["total"],
                "expense": None,
            }
        )
    for r in spent.values("category__name").annotate(total=Sum("amount")).order_by("-total"):
        rows.append({"section": expense_label, "head": r["category__name"], "income": None, "expense": r["total"]})
    total_income = sum((r["income"] for r in rows if r["income"]), Decimal(0))
    total_expense = sum((r["expense"] for r in rows if r["expense"]), Decimal(0))
    return Report(
        _("Income and expenditure"),
        [
            Column("section", _("Type")),
            Column("head", _("Head")),
            Column("income", _("Income"), "money"),
            Column("expense", _("Expense"), "money"),
        ],
        rows,
        {"income": total_income, "expense": total_expense, "balance": total_income - total_expense},
        [_("Income counts confirmed contributions and recorded other income. Expenses count approved expenses.")],
    )


def event_wise(ctx: ReportContext) -> Report:
    rows = []
    for event in ctx.events.order_by("start_date", "name"):
        t = sel.finance_totals(ctx.org, Event.objects.filter(pk=event.pk))
        rows.append(
            {
                "event": event.name,
                "status": status_label(event.status),
                "target": event.target_amount,
                "contributions": t["contributions"],
                "other_income": t["other_income"],
                "expenses": t["expenses"],
                "balance": t["balance"],
            }
        )
    return Report(
        _("Event-wise balance"),
        [
            Column("event", _("Event")),
            Column("status", _("Status")),
            Column("target", _("Target"), "money"),
            Column("contributions", _("Contributions"), "money"),
            Column("other_income", _("Other income"), "money"),
            Column("expenses", _("Expenses"), "money"),
            Column("balance", _("Balance"), "money"),
        ],
        rows,
        {k: sum((r[k] for r in rows), Decimal(0)) for k in ("contributions", "other_income", "expenses", "balance")},
    )


def audit(ctx: ReportContext) -> Report:
    from apps.audit.views import FINANCIAL_ENTITY_PREFIXES
    from apps.core.tenancy import SCOPE_ALL

    qs = AuditLog.objects.filter(organization=ctx.org).select_related("actor_user")
    qs = ctx.date_range(qs, "created_at__date")
    if ctx.org_context.scope("audit.view") != SCOPE_ALL:
        condition = Q()
        for prefix in FINANCIAL_ENTITY_PREFIXES:
            condition |= Q(entity_type__startswith=prefix)
        qs = qs.filter(condition)
    if ctx.filters.get("action"):
        qs = qs.filter(action=ctx.filters["action"])
    rows = [
        {
            "time": timezone.localtime(a.created_at).replace(microsecond=0, tzinfo=None),
            "actor": a.actor_user.full_name if a.actor_user else _("System"),
            "role": a.actor_role_code,
            "action": a.action,
            "entity": a.entity_type,
            "entity_id": a.entity_id,
            "fields": ", ".join(a.changed_fields or []),
            "ip": a.ip or "",
        }
        for a in qs.order_by("-created_at")[:MAX_ROWS]
    ]
    return Report(
        _("Audit log"),
        [
            Column("time", _("Time"), "datetime"),
            Column("actor", _("User")),
            Column("role", _("Role")),
            Column("action", _("Action")),
            Column("entity", _("Record type")),
            Column("entity_id", _("Record id")),
            Column("fields", _("Changed fields")),
            Column("ip", _("IP address")),
        ],
        rows,
        {"count": len(rows)},
    )


@dataclass(frozen=True)
class ReportDef:
    key: str
    title: str
    group: str
    build: object
    filters: tuple[str, ...]
    needs_event: bool = False


REPORTS = {
    r.key: r
    for r in [
        ReportDef("people", gettext_noop("People"), GENERAL, people, ("event",)),
        ReportDef("events", gettext_noop("Events"), GENERAL, events, ("financial_year",)),
        ReportDef(
            "contributions",
            gettext_noop("Contributions"),
            FINANCIAL,
            contributions,
            ("event", "date_from", "date_to", "fund", "contribution_type", "collector", "mode", "person"),
        ),
        ReportDef(
            "monthly-collection",
            gettext_noop("Monthly collection"),
            FINANCIAL,
            monthly_collection,
            ("event", "date_from", "date_to", "fund", "contribution_type"),
        ),
        ReportDef(
            "fund-wise", gettext_noop("Fund-wise collection"), FINANCIAL, fund_wise, ("event", "date_from", "date_to")
        ),
        ReportDef(
            "payment-mode",
            gettext_noop("Payment mode summary"),
            FINANCIAL,
            payment_mode,
            ("event", "date_from", "date_to", "collector"),
        ),
        ReportDef(
            "collector-wise",
            gettext_noop("Collector-wise collection"),
            FINANCIAL,
            collector_wise,
            ("event", "date_from", "date_to", "mode"),
        ),
        ReportDef(
            "receipts",
            gettext_noop("Receipt register"),
            FINANCIAL,
            receipts,
            ("event", "date_from", "date_to", "status"),
        ),
        ReportDef(
            "dues", gettext_noop("Pending dues"), FINANCIAL, dues, ("event", "contribution_type"), needs_event=True
        ),
        ReportDef(
            "expenses",
            gettext_noop("Expenses"),
            FINANCIAL,
            expenses,
            ("event", "date_from", "date_to", "category", "mode", "status"),
        ),
        ReportDef(
            "other-income",
            gettext_noop("Other income"),
            FINANCIAL,
            other_income,
            ("event", "date_from", "date_to", "fund"),
        ),
        ReportDef(
            "income-expense",
            gettext_noop("Income and expenditure"),
            FINANCIAL,
            income_expense,
            ("event", "date_from", "date_to"),
        ),
        ReportDef("event-wise", gettext_noop("Event-wise balance"), FINANCIAL, event_wise, ("financial_year",)),
        ReportDef("audit", gettext_noop("Audit log"), AUDIT, audit, ("date_from", "date_to", "action")),
    ]
}


def can_view(definition: ReportDef, org_context) -> bool:
    if definition.group == GENERAL:
        return org_context.has("reports.view_general")
    if definition.group == FINANCIAL:
        return org_context.has("reports.view_financial")
    return org_context.has("audit.view")


def can_export(definition: ReportDef, org_context) -> bool:
    if not org_context.has("reports.export") or not can_view(definition, org_context):
        return False
    # Secretaries read financial reports but export general ones only (PERMISSIONS.md §8.3): exporting
    # money data also needs access to the money records themselves.
    return definition.group != FINANCIAL or org_context.has("payments.view")
