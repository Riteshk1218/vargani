"""Reminders for mandatory contributions that are still due.

People with a portal login get an in-app (and, from Phase 6, push) notification. People without one are
returned with a ready-made WhatsApp link the collector can tap, because most members are reached on WhatsApp.
A person is reminded at most once per contribution type per calendar month.
"""

from decimal import Decimal
from urllib.parse import quote

from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import override

from apps.audit import services as audit
from apps.contributions.models import ContributionType
from apps.contributions.selectors import outstanding
from apps.core.money import indian_format
from apps.events.models import Event
from apps.notifications.models import Notification
from apps.notifications.services import notify
from apps.organizations.models import Organization
from apps.people.models import Person

from .linking import portal_enabled

REMIND = "dues_reminder"


def _whatsapp(person, amount, ctype, org):
    with override(org.default_language or "en"):
        text = _("Namaskar %(name)s, ₹%(amount)s is due for %(type)s (%(event)s) to %(organization)s. Thank you.") % {
            "name": person.full_name,
            "amount": amount,
            "type": ctype.name,
            "event": ctype.event.name,
            "organization": org.name,
        }
    digits = person.mobile.lstrip("+")
    return f"https://wa.me/{digits}?text={quote(text)}"


def send(ctype: ContributionType, *, request=None, actor=None) -> dict:
    org = ctype.organization
    report = outstanding(ctype, timezone.localdate())
    month_start = timezone.localdate().replace(day=1)
    already = set(
        Notification.objects.filter(
            organization=org, type=REMIND, entity_id=str(ctype.pk), created_at__date__gte=month_start
        ).values_list("recipient_id", flat=True)
    )
    people = {
        str(p.pk): p
        for p in Person.objects.filter(pk__in=[r["person"] for r in report["results"] if Decimal(r["due"]) > 0])
    }
    notified, skipped, whatsapp = 0, 0, []
    use_portal = portal_enabled(org)
    for row in report["results"]:
        due = Decimal(row["due"])
        if due <= 0:
            continue
        person = people[row["person"]]
        amount = indian_format(due)
        if use_portal and person.user_id:
            if person.user_id in already:
                skipped += 1
                continue
            notify(
                [person.user],
                REMIND,
                {"amount": amount, "type": ctype.name, "event": ctype.event.name},
                organization=org,
                entity=ctype,
                link="/app/my",
            )
            notified += 1
        elif person.mobile:
            whatsapp.append(
                {
                    "person": str(person.pk),
                    "name": person.full_name,
                    "mobile": person.mobile,
                    "due": f"{due:.2f}",
                    "whatsapp_url": _whatsapp(person, amount, ctype, org),
                }
            )
    audit.record(
        request=request,
        actor=actor,
        organization=org,
        action=REMIND,
        entity_type="contributions.contributiontype",
        entity_id=ctype.pk,
        after={"notified": notified, "whatsapp": len(whatsapp), "skipped": skipped},
    )
    return {"notified": notified, "already_reminded": skipped, "whatsapp": whatsapp}


def send_monthly():
    """Celery beat: organizations that switched on automatic reminders, active events, mandatory types."""
    total = 0
    orgs = Organization.objects.filter(
        status=Organization.Status.ACTIVE,
        settings__member_portal_enabled=True,
        settings__auto_reminders=True,
    )
    for org in orgs:
        types = ContributionType.objects.filter(
            organization=org, is_mandatory=True, is_active=True, event__status=Event.Status.ACTIVE
        ).select_related("event", "organization")
        for ctype in types:
            total += send(ctype)["notified"]
    return total
