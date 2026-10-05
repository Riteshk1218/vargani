import pytest

from apps.expenses.tests.test_expenses import new_expense
from apps.notifications.models import Notification
from apps.notifications.services import notify
from apps.payments.tests.test_payments import setup  # noqa: F401 - fixture

pytestmark = pytest.mark.django_db


def test_notifications_are_private_and_rendered_in_my_language(make_org, make_user, client_for):
    org = make_org()
    me, other = make_user(), make_user()
    me.preferred_language = "mr"
    me.save(update_fields=["preferred_language"])
    params = {"amount": "1,100.00", "number": "GC-2027-00001", "organization": org.name}
    mine = notify([me], "receipt_issued", params, organization=org)[0]
    theirs = notify([other], "receipt_issued", params, organization=org)[0]

    client = client_for(me)
    listing = client.get("/api/v1/notifications/").data
    assert [n["id"] for n in listing["results"]] == [str(mine.pk)]
    assert "1,100.00" in listing["results"][0]["body"]
    assert listing["results"][0]["title"] == "तुमच्या योगदानाबद्दल धन्यवाद"  # Marathi, not English
    assert client.get("/api/v1/notifications/unread-count/").data == {"unread": 1}

    assert client.post(f"/api/v1/notifications/{theirs.pk}/read/").status_code == 404
    assert client.post(f"/api/v1/notifications/{mine.pk}/read/").status_code == 200
    assert client.get("/api/v1/notifications/unread-count/").data == {"unread": 0}
    theirs.refresh_from_db()
    assert theirs.read_at is None

    notify([me], "receipt_issued", params, organization=org)
    assert client.post("/api/v1/notifications/read-all/").data == {"marked": 1}


def test_expense_submission_notifies_approvers_and_decision_notifies_submitter(setup, add_member, client_for):  # noqa: F811
    org = setup.org
    treasurer = add_member(org, "treasurer")
    expense_id = new_expense(client_for(treasurer, org), setup).data["id"]
    client_for(treasurer, org).post(f"/api/v1/expenses/{expense_id}/submit/")
    submitted = Notification.objects.filter(type="expense_submitted")
    assert org.admin_user in [n.recipient for n in submitted]
    assert treasurer not in [n.recipient for n in submitted]

    client_for(org.admin_user, org).post(f"/api/v1/expenses/{expense_id}/approve/")
    assert Notification.objects.filter(type="expense_approved", recipient=treasurer).exists()


def test_announcement_needs_permission_and_reaches_members(make_org, add_member, client_for):
    org = make_org()
    collector = add_member(org, "collector")
    member = add_member(org, "member")
    body = {"title": "Aarti at 7pm", "message": "Please come on time."}
    assert client_for(collector, org).post("/api/v1/announcements/", body, format="json").status_code == 403
    response = client_for(org.admin_user, org).post("/api/v1/announcements/", body, format="json")
    assert response.status_code == 201 and response.data["sent"] == 3
    shown = client_for(member).get("/api/v1/notifications/").data["results"][0]
    assert shown["title"] == "Aarti at 7pm" and shown["body"] == "Please come on time."
