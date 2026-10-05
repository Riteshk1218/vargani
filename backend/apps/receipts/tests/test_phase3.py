import pytest

from apps.contributions.models import CollectorAssignment, Contribution
from apps.organizations.models import OrganizationMembership
from apps.payments.models import Payment
from apps.payments.tests.test_payments import collect, month_line, setup  # noqa: F401 - fixture
from apps.people.models import Person
from apps.receipts.models import Receipt

pytestmark = pytest.mark.django_db


@pytest.fixture
def team(setup, add_member, client_for):  # noqa: F811
    s = setup
    s.asha = Person.objects.create(organization=s.org, full_name="Asha Kale", mobile="+919822001122")
    s.k1_user = add_member(s.org, "collector")
    s.k2_user = add_member(s.org, "collector")
    s.treasurer_user = add_member(s.org, "treasurer")
    s.k1 = client_for(s.k1_user, s.org)
    s.k2 = client_for(s.k2_user, s.org)
    s.treasurer = client_for(s.treasurer_user, s.org)
    s.k1_membership = OrganizationMembership.objects.get(organization=s.org, user=s.k1_user)
    s.k2_membership = OrganizationMembership.objects.get(organization=s.org, user=s.k2_user)
    return s


def assign(s, membership, people):
    return s.admin.post(
        "/api/v1/collector-assignments/bulk/",
        {"event": str(s.event.pk), "collector": str(membership.pk), "people": [str(p.pk) for p in people]},
        format="json",
    )


def test_collectors_collect_only_from_assigned_people(team):
    s = team
    assert assign(s, s.k1_membership, [s.ritesh]).status_code == 201
    assert [p["full_name"] for p in s.k1.get("/api/v1/people/").data["results"]] == ["Ritesh Patil"]
    assert s.k2.get("/api/v1/people/").data["count"] == 0
    assert collect(s.k1, s, [month_line(s, "2027-04-01", "500")], url="/api/v1/collections/").status_code == 201
    assert collect(s.k1, s, [month_line(s, "2027-04-01", "500")], payer=s.asha).status_code == 403
    assert collect(s.k2, s, [month_line(s, "2027-04-01", "500")]).status_code == 403

    # Re-assigning moves the person and keeps history.
    assert assign(s, s.k2_membership, [s.ritesh]).status_code == 201
    assert CollectorAssignment.objects.filter(person=s.ritesh).count() == 2
    assert CollectorAssignment.objects.filter(person=s.ritesh, is_active=True).get().collector == s.k2_membership
    assert collect(s.k1, s, [month_line(s, "2027-05-01", "500")]).status_code == 403
    assert collect(s.k2, s, [month_line(s, "2027-05-01", "500")]).status_code == 201

    mine = s.k2.get("/api/v1/collector-assignments/?is_active=true").data
    assert mine["count"] == 1
    assert s.k1.get("/api/v1/collector-assignments/?is_active=true").data["count"] == 0
    assert s.k1.post("/api/v1/collector-assignments/bulk/", {}, format="json").status_code == 403
    assignment = CollectorAssignment.objects.get(person=s.ritesh, is_active=True)
    assert s.admin.post(f"/api/v1/collector-assignments/{assignment.pk}/end/").status_code == 200
    assert s.k2.get("/api/v1/people/").data["count"] == 0


def test_only_collecting_roles_can_be_assigned(team, add_member):
    s = team
    volunteer = add_member(s.org, "volunteer")
    membership = OrganizationMembership.objects.get(organization=s.org, user=volunteer)
    assert assign(s, membership, [s.ritesh]).status_code == 400


def test_collector_dashboard_and_performance(team):
    s = team
    assign(s, s.k1_membership, [s.ritesh, s.asha])
    collect(s.k1, s, [month_line(s, "2027-04-01", "500")])
    collect(s.k1, s, [month_line(s, "2027-04-01", "300")], payer=s.asha, mode="upi")
    data = s.k1.get(f"/api/v1/collectors/me/dashboard/?event={s.event.pk}").data
    assert data["today"] == "800.00" and data["assigned"] == 2 and data["by_mode"]["upi"] == "300.00"
    assert len(data["recent_receipts"]) == 2
    rows = s.treasurer.get(f"/api/v1/collectors/?event={s.event.pk}").data["results"]
    assert rows[0]["total"] == "800.00" and rows[0]["assigned"] == 2
    own = s.k1.get(f"/api/v1/collectors/?event={s.event.pk}").data["results"]
    assert len(own) == 1 and own[0]["name"] == s.k1_user.full_name


def test_receipt_pdf_renders_in_each_language(team):
    s = team
    payment = collect(s.admin, s, [month_line(s, "2027-04-01", "1250.50")]).data
    receipt_id = payment["receipt"]["id"]
    for language in ("en", "mr", "hi"):
        Receipt.objects.filter(pk=receipt_id).update(language=language)
        response = s.admin.get(f"/api/v1/receipts/{receipt_id}/pdf/")
        assert response.status_code == 200 and response["Content-Type"] == "application/pdf"
        assert response.content.startswith(b"%PDF")


def test_share_link_and_public_receipt(team, api):
    s = team
    receipt_id = collect(s.admin, s, [month_line(s, "2027-04-01", "500")]).data["receipt"]["id"]
    share = s.admin.post(f"/api/v1/receipts/{receipt_id}/share/").data
    assert share["whatsapp_url"].startswith("https://wa.me/919812345678?text=")
    assert "GC-2027-00001" in share["whatsapp_text"]
    token = share["share_url"].rsplit("/", 1)[1]
    public = api.get(f"/api/v1/public/receipts/{token}/")
    assert public.status_code == 200 and public.data["receipt_number"] == "GC-2027-00001"
    assert "collector" not in public.data["snapshot"]
    assert api.get(f"/api/v1/public/receipts/{token}/pdf/").content.startswith(b"%PDF")
    assert api.get("/api/v1/public/receipts/not-a-real-token/").status_code == 404


def test_void_and_correction_workflow(team):
    s = team
    assign(s, s.k1_membership, [s.ritesh])
    payment = collect(s.k1, s, [month_line(s, "2027-04-01", "5000")]).data  # typo: should be 500
    receipt_id = payment["receipt"]["id"]

    assert s.k2.post(f"/api/v1/receipts/{receipt_id}/void-request/", {"reason": "x"}).status_code == 404
    assert s.k1.post(f"/api/v1/receipts/{receipt_id}/void-request/", {"reason": ""}).status_code == 422
    request = s.k1.post(f"/api/v1/receipts/{receipt_id}/void-request/", {"reason": "Typed 5000 instead of 500"})
    assert request.status_code == 201
    assert s.k1.post(f"/api/v1/receipts/{receipt_id}/void-request/", {"reason": "again"}).status_code == 409
    assert s.k1.post(f"/api/v1/receipt-void-requests/{request.data['id']}/approve/").status_code == 403

    approved = s.treasurer.post(f"/api/v1/receipt-void-requests/{request.data['id']}/approve/", {"reason": "OK"})
    assert approved.status_code == 200 and approved.data["status"] == "approved"
    receipt = Receipt.objects.get(pk=receipt_id)
    assert receipt.status == "void" and receipt.receipt_number == "GC-2027-00001"
    assert Payment.objects.get(pk=payment["id"]).status == "cancelled"
    assert set(Contribution.objects.filter(payment_id=payment["id"]).values_list("status", flat=True)) == {"cancelled"}
    assert s.admin.get(f"/api/v1/contributions/summary/?event={s.event.pk}").data["collected"] == "0.00"
    assert s.admin.get(f"/api/v1/receipts/{receipt_id}/pdf/").status_code == 200  # void receipts still print

    # Correction: the right payment, linked to the voided receipt. Collectors cannot do this themselves.
    corrected = {"replaces_receipt": receipt_id}
    assert collect(s.k1, s, [month_line(s, "2027-04-01", "500")], **corrected).status_code == 403
    response = collect(s.treasurer, s, [month_line(s, "2027-04-01", "500")], **corrected)
    assert response.status_code == 201, response.data
    new_receipt = s.admin.get(f"/api/v1/receipts/{response.data['receipt']['id']}/").data
    assert new_receipt["replaces_receipt_number"] == "GC-2027-00001"
    assert s.admin.get(f"/api/v1/receipts/{receipt_id}/").data["replaced_by"]["receipt_number"] == "GC-2027-00002"
    assert collect(s.treasurer, s, [month_line(s, "2027-04-01", "500")], **corrected).status_code == 400


def test_requester_cannot_approve_own_void_unless_admin(team):
    s = team
    receipt_id = collect(s.treasurer, s, [month_line(s, "2027-04-01", "500")]).data["receipt"]["id"]
    vr = s.treasurer.post(f"/api/v1/receipts/{receipt_id}/void-request/", {"reason": "Duplicate"}).data
    assert s.treasurer.post(f"/api/v1/receipt-void-requests/{vr['id']}/approve/").status_code == 422
    assert s.treasurer.post(f"/api/v1/receipt-void-requests/{vr['id']}/reject/", {"reason": "No"}).status_code == 200
    receipt_id = collect(s.admin, s, [month_line(s, "2027-05-01", "500")]).data["receipt"]["id"]
    vr = s.admin.post(f"/api/v1/receipts/{receipt_id}/void-request/", {"reason": "Duplicate"}).data
    assert s.admin.post(f"/api/v1/receipt-void-requests/{vr['id']}/approve/").status_code == 200
    assert s.admin.post(f"/api/v1/receipt-void-requests/{vr['id']}/approve/").status_code == 409


def test_amount_in_words():
    from apps.core.words import rupees_in_words

    assert rupees_in_words("2600") == "Two Thousand Six Hundred Rupees Only"
    assert rupees_in_words("125050.50") == "One Lakh Twenty Five Thousand Fifty Rupees and Fifty Paise Only"
    assert rupees_in_words("10000000") == "One Crore Rupees Only"
