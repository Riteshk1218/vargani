# ruff: noqa: F811
"""Admin studio: admins rename Collect fields, change the payment mode dropdown and add their own dropdowns."""

import pytest

from apps.payments.models import Payment
from apps.payments.tests.test_payments import collect, setup  # noqa: F401
from apps.receipts.models import Receipt

pytestmark = pytest.mark.django_db


def studio_url(s):
    return f"/api/v1/organizations/{s.org.pk}/form-studio/"


def save(client, s, data):
    return client.put(studio_url(s), data, format="json")


def donation(s, amount="501"):
    return [{"contribution_type": str(s.donation.pk), "amount": amount}]


WARD = {"label": "Ward", "options": ["Ward 1", "Ward 2", " Ward 2 ", ""], "required": True}


def test_admin_sets_up_the_collect_form(setup):
    s = setup
    assert s.admin.get(studio_url(s)).data == {"labels": {}, "modes": {}, "custom_fields": []}
    response = save(
        s.admin,
        s,
        {
            "labels": {"amount": "  Rakkam ", "notes": ""},
            "modes": {"cheque": {"hidden": True}, "upi": {"label": "PhonePe / GPay"}},
            "custom_fields": [WARD],
        },
    )
    assert response.status_code == 200, response.data
    data = response.data
    assert data["labels"] == {"amount": "Rakkam"}
    assert data["modes"] == {
        "cheque": {"label": "", "hidden": True},
        "upi": {"label": "PhonePe / GPay", "hidden": False},
    }
    [ward] = data["custom_fields"]
    assert ward["key"].startswith("f_") and ward["options"] == ["Ward 1", "Ward 2"]
    assert ward["required"] is True and ward["active"] is True

    # Everyone in the organization gets it with their organization details.
    me = s.admin.get(f"/api/v1/me/organizations/{s.org.pk}/").data
    assert me["form_studio"] == data

    # Renaming keeps the key, so older collections stay linked.
    renamed = save(s.admin, s, {**data, "custom_fields": [{**ward, "label": "Prabhag", "options": ["1", "2"]}]})
    assert renamed.status_code == 200
    assert renamed.data["custom_fields"][0]["key"] == ward["key"]
    assert renamed.data["custom_fields"][0]["label"] == "Prabhag"


def test_studio_rejects_bad_setups(setup):
    s = setup
    assert save(s.admin, s, {"labels": {"nope": "x"}}).status_code == 400
    assert save(s.admin, s, {"labels": {"amount": "x" * 61}}).status_code == 400
    all_hidden = {m: {"hidden": True} for m in ["cash", "upi", "bank_transfer", "cheque", "other"]}
    assert save(s.admin, s, {"modes": all_hidden}).status_code == 400
    assert save(s.admin, s, {"modes": {"online": {"label": "x"}}}).status_code == 400
    assert save(s.admin, s, {"custom_fields": [{"label": "Ward", "options": []}]}).status_code == 400
    assert save(s.admin, s, {"custom_fields": [{"label": "", "options": ["1"]}]}).status_code == 400
    assert (
        save(s.admin, s, {"custom_fields": [{"key": "f_made_up", "label": "W", "options": ["1"]}]}).status_code == 400
    )


def test_dropdown_left_out_is_switched_off_not_lost(setup):
    s = setup
    [ward] = save(s.admin, s, {"custom_fields": [WARD]}).data["custom_fields"]
    data = save(s.admin, s, {"custom_fields": []}).data
    assert data["custom_fields"] == [{**ward, "active": False}]


def test_only_admins_change_the_studio(setup, add_member, client_for):
    s = setup
    collector = client_for(add_member(s.org, "collector"), s.org)
    assert collector.get(studio_url(s)).status_code == 200
    assert save(collector, s, {"labels": {"amount": "x"}}).status_code == 403


def test_collection_saves_the_dropdown_answer_on_payment_and_receipt(setup):
    s = setup
    studio = save(s.admin, s, {"modes": {"cash": {"label": "Rokh"}}, "custom_fields": [WARD]}).data
    key = studio["custom_fields"][0]["key"]

    missing = collect(s.admin, s, donation(s))
    assert missing.status_code == 400 and key in missing.data["error"]["details"]["custom_fields"]
    wrong = collect(s.admin, s, donation(s), custom_fields={key: "Ward 9"})
    assert wrong.status_code == 400
    unknown = collect(s.admin, s, donation(s), custom_fields={key: "Ward 1", "f_other": "x"})
    assert unknown.status_code == 400

    response = collect(s.admin, s, donation(s), custom_fields={key: "Ward 2"})
    assert response.status_code == 201, response.data
    assert response.data["custom_fields"] == [{"key": key, "label": "Ward", "value": "Ward 2"}]
    assert Payment.objects.get(pk=response.data["id"]).custom_fields == {key: "Ward 2"}
    snapshot = Receipt.objects.get(payment_id=response.data["id"]).snapshot
    assert snapshot["custom_fields"] == [{"label": "Ward", "value": "Ward 2"}]
    assert snapshot["mode_label"] == "Rokh"


def test_collection_without_studio_is_unchanged(setup):
    s = setup
    response = collect(s.admin, s, donation(s))
    assert response.status_code == 201
    assert response.data["custom_fields"] == []
    snapshot = Receipt.objects.get(payment_id=response.data["id"]).snapshot
    assert snapshot["custom_fields"] == [] and snapshot["mode_label"] == ""
