"""Creates a demo organization through the real API so the website and the app can be tried.

Development servers only (needs OTP_DEBUG_ECHO=true). Safe to run again: it stops if the demo
admin already exists. Usage: DEMO_API=http://localhost:8000 python scripts/seed_demo.py
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid

B = os.environ.get("DEMO_API", "http://localhost:8000").rstrip("/") + "/api/v1"
PASSWORD = "DemoPass#2026"


def call(method, path, body=None, tok=None, org=None, headers=None, ok=True):
    h = {"Content-Type": "application/json", "X-Client-Type": "app", **(headers or {})}
    if tok:
        h["Authorization"] = "Bearer " + tok
    if org:
        h["X-Organization-ID"] = org
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(B + path, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            t = r.read()
            return json.loads(t) if t else {}
    except urllib.error.HTTPError as e:
        if not ok:
            return None
        sys.exit(f"Demo setup failed at {method} {path}: {e.code} {e.read().decode()[:400]}")


def rows(data):
    return data if isinstance(data, list) else data["results"]


def account(name, email, mobile=None):
    body = {"full_name": name, "email": email, "password": PASSWORD}
    if mobile:
        body["mobile"] = mobile
    r = call("POST", "/auth/register/", body)
    call("POST", "/auth/verify/", {"destination": email, "code": r["debug_code"]})
    return call("POST", "/auth/login/", {"identifier": email, "password": PASSWORD})["access"]


def main():
    for _ in range(90):
        try:
            urllib.request.urlopen(B + "/health/", timeout=5)
            break
        except Exception:
            time.sleep(2)
    else:
        sys.exit("The API did not start.")

    if call("POST", "/auth/login/", {"identifier": "admin@demo.test", "password": PASSWORD}, ok=False):
        print("Demo data is already there.")
        return

    tok = account("Asha Admin", "admin@demo.test", "9800000001")
    org = call(
        "POST",
        "/organizations/",
        {
            "name": "Demo Mitra Mandal",
            "city": "Pune",
            "state": "Maharashtra",
            "financial_year": {"label": "2026-27", "start_date": "2026-04-01", "end_date": "2027-03-31"},
        },
        tok,
    )
    O = org["id"]
    fy = call("GET", f"/me/organizations/{O}/", None, tok, O)["current_financial_year"]["id"]
    ev = call(
        "POST",
        "/events/",
        {
            "name": "Ganesh Chaturthi 2026",
            "template": "festival",
            "code": "GC",
            "financial_year": fy,
            "start_date": "2026-08-01",
            "end_date": "2026-12-31",
            "thank_you_message": "Ganpati Bappa Morya! Thank you for your support.",
        },
        tok,
        O,
    )
    E = ev["id"]
    fund = call("POST", "/funds/", {"event": E, "name": "Utsav Fund"}, tok, O)
    vargani = call(
        "POST",
        "/contribution-types/",
        {
            "event": E,
            "fund": fund["id"],
            "name": "Ganesh Vargani",
            "kind": "one_time",
            "suggested_min": "500.00",
            "suggested_max": "700.00",
            "is_mandatory": True,
            "target_amount": "600.00",
        },
        tok,
        O,
    )
    donation = call(
        "POST", "/contribution-types/", {"event": E, "fund": fund["id"], "name": "Donation", "kind": "one_time"}, tok, O
    )
    call("PATCH", f"/organizations/{O}/settings/", {"member_portal_enabled": True}, tok, O)

    people = []
    for name, mobile in [
        ("Ritesh Patil", "9822001122"),
        ("Sunita More", "9822001133"),
        ("Vikas Jadhav", "9822001144"),
        ("Meena Kulkarni", "9822001155"),
    ]:
        p = call(
            "POST",
            "/people/",
            {"full_name": name, "mobile": mobile, "area": "Shivaji Nagar", "person_types": ["member"]},
            tok,
            O,
        )
        call("POST", "/event-participants/", {"event": E, "person": p["id"]}, tok, O)
        people.append(p)

    roles = {r["code"]: r["id"] for r in rows(call("GET", "/roles/", None, tok, O))}
    inv = call(
        "POST",
        "/invitations/",
        {"full_name": "Kiran Collector", "email": "collector@demo.test", "role_id": roles["collector"]},
        tok,
        O,
    )
    ctok = account("Kiran Collector", "collector@demo.test")
    call("POST", "/invitations/accept/", {"token": inv["invite_url"].rsplit("/", 1)[1]}, ctok)
    collector = [m for m in rows(call("GET", "/members/", None, tok, O)) if m["role"]["code"] == "collector"][0]
    call(
        "POST",
        "/collector-assignments/bulk/",
        {"event": E, "collector": collector["id"], "people": [p["id"] for p in people[:3]]},
        tok,
        O,
    )

    def collect(t, person, lines, mode="cash", ref=""):
        call(
            "POST",
            "/collections/",
            {"event": E, "payer": person and person["id"], "mode": mode, "reference_number": ref, "lines": lines},
            t,
            O,
            headers={"Idempotency-Key": str(uuid.uuid4())},
        )

    collect(ctok, people[0], [{"contribution_type": vargani["id"], "amount": "300.00"}])
    collect(ctok, people[0], [{"contribution_type": vargani["id"], "amount": "200.00"}], "upi", "UPI4471")
    collect(
        ctok,
        people[1],
        [
            {"contribution_type": vargani["id"], "amount": "700.00"},
            {"contribution_type": donation["id"], "amount": "501.00"},
        ],
        "upi",
        "UPI4472",
    )
    collect(tok, people[3], [{"contribution_type": donation["id"], "amount": "1100.00"}], "bank_transfer", "NEFT9921")
    collect(ctok, None, [{"contribution_type": donation["id"], "amount": "151.00"}])  # anonymous (no name)

    # Expenses: one approved by the admin, one sent by the collector and waiting for approval.
    cats = {c["name"]: c["id"] for c in rows(call("GET", "/expense-categories/", None, tok, O))}
    decoration = call(
        "POST",
        "/expenses/",
        {
            "event": E,
            "category": cats["Decoration"],
            "amount": "3500.00",
            "payee": "Shree Decorators",
            "description": "Pandal flowers and lights",
            "mode": "cash",
        },
        tok,
        O,
    )
    call("POST", f"/expenses/{decoration['id']}/submit/", None, tok, O)
    call("POST", f"/expenses/{decoration['id']}/approve/", None, tok, O)
    flowers = call(
        "POST",
        "/expenses/",
        {
            "event": E,
            "category": cats.get("Puja", cats["Other"]),
            "amount": "450.00",
            "description": "Flowers for evening aarti",
            "mode": "upi",
        },
        ctok,
        O,
    )
    call("POST", f"/expenses/{flowers['id']}/submit/", None, ctok, O)
    print("Demo data created.")


if __name__ == "__main__":
    main()
