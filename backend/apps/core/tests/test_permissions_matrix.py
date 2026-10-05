"""Role × endpoint matrix (spec §33 tests 5 and 6, PERMISSIONS.md §8.3).

Allowed means "not refused with 403"; denied means 403 permission_denied.
"""

import pytest

from apps.organizations.models import FinancialYear

pytestmark = pytest.mark.django_db

ROLES = ["org_admin", "treasurer", "secretary", "collector", "volunteer", "member"]


def endpoint_cases(org):
    fy = FinancialYear.objects.get(organization=org)
    return {
        "view people": ("get", "/api/v1/people/", None),
        "add person": ("post", "/api/v1/people/", {"full_name": "New"}),
        "edit organization": ("patch", f"/api/v1/organizations/{org.pk}/", {"city": "Pune"}),
        "change org settings": ("patch", f"/api/v1/organizations/{org.pk}/settings/", {"member_portal_enabled": True}),
        "remove logo": ("delete", f"/api/v1/organizations/{org.pk}/logo/", None),
        "view members": ("get", "/api/v1/members/", None),
        "invite user": ("post", "/api/v1/invitations/", {"email": "new@example.com", "role_id": "x"}),
        "view financial years": ("get", "/api/v1/financial-years/", None),
        "create financial year": (
            "post",
            "/api/v1/financial-years/",
            {"label": "N", "start_date": "2030-04-01", "end_date": "2031-03-31"},
        ),
        "close financial year": ("post", f"/api/v1/financial-years/{fy.pk}/close/", None),
        "view events": ("get", "/api/v1/events/", None),
        "create event": ("post", "/api/v1/events/", {"name": "E", "financial_year": str(fy.pk)}),
        "view audit log": ("get", "/api/v1/audit-logs/", None),
        "view roles": ("get", "/api/v1/roles/", None),
        "view funds": ("get", "/api/v1/funds/", None),
        "manage funds": ("post", "/api/v1/funds/", {}),
        "view contribution types": ("get", "/api/v1/contribution-types/", None),
        "manage contribution types": ("post", "/api/v1/contribution-types/", {}),
        "record payment": ("post", "/api/v1/payments/", {}),
        "record collection": ("post", "/api/v1/collections/", {}),
        "view payments": ("get", "/api/v1/payments/", None),
        "view contributions": ("get", "/api/v1/contributions/", None),
        "view receipts": ("get", "/api/v1/receipts/", None),
        "view expenses": ("get", "/api/v1/expenses/", None),
        "create expense": ("post", "/api/v1/expenses/", {}),
        "manage expense categories": ("post", "/api/v1/expense-categories/", {}),
        "other income": ("get", "/api/v1/other-income/", None),
        "list reports": ("get", "/api/v1/reports/", None),
        "general report": ("get", "/api/v1/reports/people/", None),
        "financial report": ("get", "/api/v1/reports/income-expense/", None),
        "audit report": ("get", "/api/v1/reports/audit/", None),
        "export general report": ("post", "/api/v1/reports/people/exports/", {"format": "csv"}),
        "export financial report": ("post", "/api/v1/reports/income-expense/exports/", {"format": "csv"}),
    }


EXPECTED = {
    #                         admin treas  secr   coll   volun  member
    "view people": (1, 1, 1, 1, 1, 0),
    "add person": (1, 1, 1, 0, 0, 0),
    "edit organization": (1, 0, 0, 0, 0, 0),
    "change org settings": (1, 0, 0, 0, 0, 0),
    "remove logo": (1, 0, 0, 0, 0, 0),
    "view members": (1, 0, 0, 0, 0, 0),
    "invite user": (1, 0, 0, 0, 0, 0),
    "view financial years": (1, 1, 1, 1, 0, 0),
    "create financial year": (1, 0, 0, 0, 0, 0),
    "close financial year": (1, 0, 0, 0, 0, 0),
    "view events": (1, 1, 1, 1, 1, 1),
    "create event": (1, 0, 1, 0, 0, 0),
    "view audit log": (1, 1, 0, 0, 0, 0),
    "view roles": (1, 0, 0, 0, 0, 0),
    "view funds": (1, 1, 1, 1, 0, 0),
    "manage funds": (1, 1, 0, 0, 0, 0),
    "view contribution types": (1, 1, 1, 1, 0, 0),
    "manage contribution types": (1, 1, 0, 0, 0, 0),
    # Collectors hold the permission; which people they may collect from is checked per payer (assignments).
    "record payment": (1, 1, 0, 1, 0, 0),
    "record collection": (1, 1, 0, 1, 0, 0),
    "view payments": (1, 1, 0, 1, 0, 0),
    "view contributions": (1, 1, 0, 1, 0, 0),
    "view receipts": (1, 1, 0, 1, 0, 0),
    "view expenses": (1, 1, 0, 0, 0, 0),
    "create expense": (1, 1, 0, 0, 0, 0),
    "manage expense categories": (1, 1, 0, 0, 0, 0),
    "other income": (1, 1, 0, 0, 0, 0),
    "list reports": (1, 1, 1, 0, 0, 0),
    "general report": (1, 1, 1, 0, 0, 0),
    "financial report": (1, 1, 1, 0, 0, 0),
    "audit report": (1, 1, 0, 0, 0, 0),
    "export general report": (1, 1, 1, 0, 0, 0),
    "export financial report": (1, 1, 0, 0, 0, 0),
}


@pytest.mark.parametrize("role_index,role", list(enumerate(ROLES)))
def test_role_matrix(make_org, add_member, client_for, role_index, role):
    org = make_org()
    user = org.admin_user if role == "org_admin" else add_member(org, role)
    client = client_for(user, org)
    failures = []
    for name, (method, url, payload) in endpoint_cases(org).items():
        response = getattr(client, method)(url, payload, format="json")
        allowed = response.status_code != 403
        if allowed != bool(EXPECTED[name][role_index]):
            failures.append(f"{name}: got {response.status_code}")
    assert not failures, f"{role}: {failures}"
