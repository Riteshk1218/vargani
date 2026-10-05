"""Code-defined permission catalog and system roles (see docs/architecture/PERMISSIONS.md).

Synced to the database after every `migrate`, so the catalog in code is always the source of truth.
"""

from django.db import transaction

ALL, OWN, ASSIGNED, SELF = "all", "own", "assigned", "self"

PERMISSIONS = {
    # code: (module, description)
    "organization.view": ("organization", "See organization profile"),
    "organization.manage": ("organization", "Edit profile, logo and settings"),
    "financial_years.view": ("financial_years", "See financial years"),
    "financial_years.manage": ("financial_years", "Create, close and select financial years"),
    "members.view": ("members", "See users with access"),
    "members.manage": ("members", "Invite users, change roles, suspend access"),
    "roles.manage": ("roles", "Create and edit custom roles"),
    "events.view": ("events", "See events"),
    "events.manage": ("events", "Create, edit and close events and participants"),
    "funds.view": ("funds", "See funds"),
    "funds.manage": ("funds", "Configure funds"),
    "contribution_types.view": ("contribution_types", "See contribution types"),
    "contribution_types.manage": ("contribution_types", "Configure contribution types"),
    "people.view": ("people", "See people"),
    "people.create": ("people", "Quick-add a contributor"),
    "people.manage": ("people", "Edit, archive and import people"),
    "collectors.manage": ("collectors", "Assign people to collectors"),
    "collectors.view_performance": ("collectors", "See collector totals"),
    "contributions.view": ("contributions", "See contributions"),
    "contributions.create": ("contributions", "Record collections"),
    "payments.view": ("payments", "See payments"),
    "payments.create": ("payments", "Record payments"),
    "payments.cancel_pending": ("payments", "Cancel pending payments"),
    "receipts.view": ("receipts", "View, download and print receipts"),
    "receipts.share": ("receipts", "Share receipts"),
    "receipts.void_request": ("receipts", "Request a receipt void or correction"),
    "receipts.void_approve": ("receipts", "Approve receipt voids and corrections"),
    "expenses.view": ("expenses", "See expenses"),
    "expenses.create": ("expenses", "Create and submit expenses"),
    "expenses.approve": ("expenses", "Approve or reject expenses"),
    "other_income.manage": ("other_income", "Record other income"),
    "dashboard.view_financial": ("dashboard", "See financial dashboard"),
    "reports.view_general": ("reports", "See people and event reports"),
    "reports.view_financial": ("reports", "See financial reports"),
    "reports.export": ("reports", "Export reports"),
    "audit.view": ("audit", "See the audit log"),
    "notifications.send": ("notifications", "Send announcements and reminders"),
    "portal.self": ("portal", "Member portal: own data only"),
}

_ADMIN = {code: ALL for code in PERMISSIONS}

SYSTEM_ROLES = {
    # code: (name, rank, description, {permission: scope})
    "org_admin": ("Organization Admin", 10, "Full control of the organization", _ADMIN),
    "treasurer": (
        "Treasurer",
        20,
        "Contributions, payments, receipts, expenses and financial reports",
        {
            "organization.view": ALL,
            "financial_years.view": ALL,
            "events.view": ALL,
            "funds.view": ALL,
            "funds.manage": ALL,
            "contribution_types.view": ALL,
            "contribution_types.manage": ALL,
            "people.view": ALL,
            "people.create": ALL,
            "collectors.manage": ALL,
            "collectors.view_performance": ALL,
            "contributions.view": ALL,
            "contributions.create": ALL,
            "payments.view": ALL,
            "payments.create": ALL,
            "payments.cancel_pending": ALL,
            "receipts.view": ALL,
            "receipts.share": ALL,
            "receipts.void_request": ALL,
            "receipts.void_approve": ALL,
            "expenses.view": ALL,
            "expenses.create": ALL,
            "expenses.approve": ALL,
            "other_income.manage": ALL,
            "dashboard.view_financial": ALL,
            "reports.view_general": ALL,
            "reports.view_financial": ALL,
            "reports.export": ALL,
            "audit.view": "financial",
            "portal.self": SELF,
        },
    ),
    "secretary": (
        "Secretary",
        30,
        "People, events and reports",
        {
            "organization.view": ALL,
            "financial_years.view": ALL,
            "events.view": ALL,
            "events.manage": ALL,
            "funds.view": ALL,
            "contribution_types.view": ALL,
            "people.view": ALL,
            "people.create": ALL,
            "people.manage": ALL,
            "collectors.manage": ALL,
            "dashboard.view_financial": ALL,
            "reports.view_general": ALL,
            "reports.view_financial": ALL,
            "reports.export": ALL,
            "notifications.send": ALL,
            "portal.self": SELF,
        },
    ),
    "collector": (
        "Karyakarta / Collector",
        40,
        "Collects contributions from assigned people",
        {
            "organization.view": ALL,
            "financial_years.view": ALL,
            "events.view": ALL,
            "funds.view": ALL,
            "contribution_types.view": ALL,
            "people.view": ASSIGNED,
            "people.create": ASSIGNED,
            "collectors.view_performance": OWN,
            "contributions.view": OWN,
            "contributions.create": ASSIGNED,
            "payments.view": OWN,
            "payments.create": ASSIGNED,
            "receipts.view": OWN,
            "receipts.share": OWN,
            "receipts.void_request": OWN,
            "portal.self": SELF,
        },
    ),
    "volunteer": (
        "Volunteer",
        50,
        "Event help without financial access",
        {"organization.view": ALL, "events.view": ALL, "people.view": ASSIGNED, "portal.self": SELF},
    ),
    "member": (
        "Member",
        60,
        "Own profile, contributions and receipts only",
        {"organization.view": ALL, "events.view": SELF, "portal.self": SELF},
    ),
}

ADMIN_ROLE = "org_admin"


def sync_catalog(**kwargs):
    from .models import Permission, Role, RolePermission

    with transaction.atomic():
        existing = {p.code: p for p in Permission.objects.all()}
        for code, (module, description) in PERMISSIONS.items():
            perm = existing.get(code)
            if perm is None:
                existing[code] = Permission.objects.create(code=code, module=module, description=description)
            elif (perm.module, perm.description) != (module, description):
                perm.module, perm.description = module, description
                perm.save(update_fields=["module", "description"])
        Permission.objects.exclude(code__in=PERMISSIONS.keys()).delete()

        for code, (name, rank, description, grants) in SYSTEM_ROLES.items():
            role, _ = Role.objects.update_or_create(
                organization=None,
                code=code,
                defaults={"name": name, "rank": rank, "description": description, "is_system": True},
            )
            current = {rp.permission.code: rp for rp in role.role_permissions.select_related("permission")}
            for perm_code, scope in grants.items():
                rp = current.pop(perm_code, None)
                if rp is None:
                    RolePermission.objects.create(role=role, permission=existing[perm_code], scope=scope)
                elif rp.scope != scope:
                    rp.scope = scope
                    rp.save(update_fields=["scope"])
            for stale in current.values():
                stale.delete()
