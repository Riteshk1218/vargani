from datetime import date
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError, transaction

from apps.audit.models import AuditLog
from apps.expenses.models import Expense, ExpenseCategory, OtherIncome
from apps.organizations.models import OrganizationMembership
from apps.payments.tests.test_payments import setup  # noqa: F401 - fixture
from conftest import png_bytes

pytestmark = pytest.mark.django_db
TODAY = date.today().isoformat()


def category(s, name="Decoration"):
    return ExpenseCategory.objects.get(organization=s.org, name=name)


def new_expense(client, s, amount="2500.50", **extra):
    payload = {
        "event": str(s.event.pk),
        "category": str(category(s).pk),
        "amount": amount,
        "expense_date": TODAY,
        "mode": "cash",
        "payee": "Shree Decorators",
        **extra,
    }
    return client.post("/api/v1/expenses/", payload, format="json")


def test_default_categories_are_seeded_for_every_new_organization(setup, make_org):  # noqa: F811
    names = set(ExpenseCategory.objects.filter(organization=setup.org).values_list("name", flat=True))
    assert {"Decoration", "Sound", "Pandal", "Electricity", "Other"} <= names
    other = make_org("Second Mandal")
    assert ExpenseCategory.objects.filter(organization=other).count() == len(names)
    # Categories are per organization, never shared.
    assert not ExpenseCategory.objects.filter(organization=other, pk=category(setup).pk).exists()


def test_full_flow_draft_submit_approve(setup, add_member, client_for):  # noqa: F811
    s = setup
    treasurer = add_member(s.org, "treasurer")
    t = client_for(treasurer, s.org)
    response = new_expense(t, s)
    assert response.status_code == 201, response.data
    expense_id = response.data["id"]
    assert response.data["status"] == "draft" and response.data["amount"] == "2500.50"

    assert t.patch(f"/api/v1/expenses/{expense_id}/", {"amount": "2600.00"}, format="json").data["amount"] == "2600.00"
    assert t.post(f"/api/v1/expenses/{expense_id}/submit/").data["status"] == "submitted"

    # Four-eyes rule: the treasurer who submitted cannot approve; the admin can.
    denied = t.post(f"/api/v1/expenses/{expense_id}/approve/")
    assert denied.status_code == 422
    approved = s.admin.post(f"/api/v1/expenses/{expense_id}/approve/")
    assert approved.status_code == 200 and approved.data["status"] == "approved"

    # Approved expenses are fixed: no edits, only void (by an approver, with a reason).
    assert t.patch(f"/api/v1/expenses/{expense_id}/", {"amount": "1"}, format="json").status_code == 409
    assert s.admin.post(f"/api/v1/expenses/{expense_id}/void/", {"reason": ""}, format="json").status_code == 400
    voided = s.admin.post(f"/api/v1/expenses/{expense_id}/void/", {"reason": "Duplicate bill"}, format="json")
    assert voided.data["status"] == "void" and voided.data["void_reason"] == "Duplicate bill"
    actions = set(AuditLog.objects.filter(entity_id=expense_id).values_list("action", flat=True))
    assert {"create", "update", "expense_submit", "approve", "void"} <= actions


def test_reject_then_edit_goes_back_to_draft(setup, add_member, client_for):  # noqa: F811
    s = setup
    t = client_for(add_member(s.org, "treasurer"), s.org)
    expense_id = new_expense(t, s).data["id"]
    t.post(f"/api/v1/expenses/{expense_id}/submit/")
    assert s.admin.post(f"/api/v1/expenses/{expense_id}/reject/", {}, format="json").status_code == 400
    rejected = s.admin.post(f"/api/v1/expenses/{expense_id}/reject/", {"reason": "Attach the bill"}, format="json")
    assert rejected.data["status"] == "rejected"
    edited = t.patch(f"/api/v1/expenses/{expense_id}/", {"description": "Bill attached"}, format="json")
    assert edited.data["status"] == "draft" and edited.data["rejection_reason"] == "Attach the bill"


def test_without_approval_setting_submit_approves(setup):  # noqa: F811
    s = setup
    s.org.settings = {**s.org.settings, "require_expense_approval": False}
    s.org.save()
    expense_id = new_expense(s.admin, s).data["id"]
    assert s.admin.post(f"/api/v1/expenses/{expense_id}/submit/").data["status"] == "approved"


def test_validation(setup):  # noqa: F811
    s = setup
    assert new_expense(s.admin, s, amount="0").status_code == 400
    assert new_expense(s.admin, s, payee="  ").status_code == 400
    assert new_expense(s.admin, s, expense_date="2099-01-01").status_code == 400
    assert new_expense(s.admin, s, mode="online").status_code == 400
    s.event.status = "closed"
    s.event.save()
    assert new_expense(s.admin, s).status_code == 422


def test_roles(setup, add_member, client_for):  # noqa: F811
    s = setup
    for role in ("secretary", "collector", "volunteer", "member"):
        client = client_for(add_member(s.org, role), s.org)
        assert client.get("/api/v1/expenses/").status_code == 403, role
        assert new_expense(client, s).status_code == 403, role
        assert client.get("/api/v1/other-income/").status_code == 403, role


def test_expenses_and_income_can_never_be_deleted_or_rewritten(setup):  # noqa: F811
    s = setup
    expense_id = new_expense(s.admin, s).data["id"]
    s.admin.post(f"/api/v1/expenses/{expense_id}/submit/")
    s.admin.post(f"/api/v1/expenses/{expense_id}/approve/")
    assert s.admin.delete(f"/api/v1/expenses/{expense_id}/").status_code == 405
    expense = Expense.objects.get(pk=expense_id)
    with pytest.raises(DatabaseError), transaction.atomic():
        Expense.objects.filter(pk=expense.pk).delete()
    with pytest.raises(DatabaseError), transaction.atomic():
        Expense.objects.filter(pk=expense.pk).update(amount=Decimal("1.00"))
    with pytest.raises(DatabaseError), transaction.atomic():
        Expense.objects.filter(pk=expense.pk).update(status="draft")

    income = OtherIncome.objects.create(
        organization=s.org,
        financial_year=s.fy,
        event=s.event,
        source="donation_box",
        amount=Decimal("5"),
        received_on=date.today(),
    )
    with pytest.raises(DatabaseError), transaction.atomic():
        OtherIncome.objects.filter(pk=income.pk).delete()
    with pytest.raises(DatabaseError), transaction.atomic():
        OtherIncome.objects.filter(pk=income.pk).update(amount=Decimal("50"))


def test_attachments(setup, settings):  # noqa: F811
    s = setup
    expense_id = new_expense(s.admin, s).data["id"]
    url = f"/api/v1/expenses/{expense_id}/attachments/"
    photo = SimpleUploadedFile("bill photo.jpg", png_bytes(fmt="JPEG"), content_type="image/jpeg")
    response = s.admin.post(url, {"file": photo}, format="multipart")
    assert response.status_code == 201, response.data
    assert response.data["content_type"] == "image/jpeg" and response.data["original_name"] == "bill photo.jpg"
    pdf = SimpleUploadedFile("bill.pdf", b"%PDF-1.4\n%fake but valid header\n", content_type="application/pdf")
    assert s.admin.post(url, {"file": pdf}, format="multipart").status_code == 201
    # The name and content type lie; the content decides.
    fake = SimpleUploadedFile("evil.png", b"<script>alert(1)</script>", content_type="image/png")
    assert s.admin.post(url, {"file": fake}, format="multipart").status_code == 415
    big = SimpleUploadedFile("big.pdf", b"%PDF-" + b"0" * (10 * 1024 * 1024), content_type="application/pdf")
    assert s.admin.post(url, {"file": big}, format="multipart").status_code == 413

    detail = s.admin.get(f"/api/v1/expenses/{expense_id}/").data
    first = detail["attachments"][0]["id"]
    download = s.admin.get(f"{url}{first}/")
    assert download.status_code == 200 and download["Content-Type"] == "image/jpeg"
    assert "attachment" in download["Content-Disposition"]
    assert b"".join(download.streaming_content)[:2] == b"\xff\xd8"

    # Bills can be removed while the expense is a draft, but not after approval.
    second = detail["attachments"][1]["id"]
    assert s.admin.delete(f"{url}{second}/").status_code == 204
    s.admin.post(f"/api/v1/expenses/{expense_id}/submit/")
    s.admin.post(f"/api/v1/expenses/{expense_id}/approve/")
    assert s.admin.delete(f"{url}{first}/").status_code == 409
    photo = SimpleUploadedFile("late.png", png_bytes(), content_type="image/png")
    assert s.admin.post(url, {"file": photo}, format="multipart").status_code == 409


def test_at_most_ten_attachments(setup):  # noqa: F811
    s = setup
    expense_id = new_expense(s.admin, s).data["id"]
    url = f"/api/v1/expenses/{expense_id}/attachments/"
    for i in range(10):
        pdf = SimpleUploadedFile(f"b{i}.pdf", b"%PDF-1.4\n", content_type="application/pdf")
        assert s.admin.post(url, {"file": pdf}, format="multipart").status_code == 201
    pdf = SimpleUploadedFile("b11.pdf", b"%PDF-1.4\n", content_type="application/pdf")
    assert s.admin.post(url, {"file": pdf}, format="multipart").status_code == 422


def test_other_income_flow(setup):  # noqa: F811
    s = setup
    payload = {
        "event": str(s.event.pk),
        "fund": str(s.fund.pk),
        "source": "donation_box",
        "amount": "1234.75",
        "received_on": TODAY,
        "mode": "cash",
        "description": "Hundi day 1",
    }
    response = s.admin.post("/api/v1/other-income/", payload, format="json")
    assert response.status_code == 201, response.data
    income_id = response.data["id"]
    # Only notes change; the amount is ignored on PATCH.
    patched = s.admin.patch(
        f"/api/v1/other-income/{income_id}/", {"amount": "1", "description": "Hundi"}, format="json"
    )
    assert patched.data["amount"] == "1234.75" and patched.data["description"] == "Hundi"
    assert s.admin.post(f"/api/v1/other-income/{income_id}/void/", {"reason": "Counted twice"}).data["status"] == "void"
    assert s.admin.post(f"/api/v1/other-income/{income_id}/void/", {"reason": "again"}).status_code == 409


def test_category_management(setup, add_member, client_for):  # noqa: F811
    s = setup
    created = s.admin.post("/api/v1/expense-categories/", {"name": "  Security  guards "}, format="json")
    assert created.status_code == 201 and created.data["name"] == "Security guards"
    assert s.admin.post("/api/v1/expense-categories/", {"name": "security GUARDS"}, format="json").status_code == 400
    archived = s.admin.patch(f"/api/v1/expense-categories/{created.data['id']}/", {"is_active": False}, format="json")
    assert archived.data["is_active"] is False
    assert new_expense(s.admin, s, category=created.data["id"]).status_code == 400
    assert s.admin.delete(f"/api/v1/expense-categories/{created.data['id']}/").status_code == 405


def test_one_person_org_admin_can_self_approve(setup):  # noqa: F811
    s = setup
    assert OrganizationMembership.objects.filter(organization=s.org).count() == 1
    expense_id = new_expense(s.admin, s).data["id"]
    s.admin.post(f"/api/v1/expenses/{expense_id}/submit/")
    assert s.admin.post(f"/api/v1/expenses/{expense_id}/approve/").data["status"] == "approved"
