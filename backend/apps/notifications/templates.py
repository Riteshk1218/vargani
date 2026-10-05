"""Notification texts. Params are filled in at read time, in the reader's language.

Amounts are pre-formatted strings in params; names are user data and are never translated.
"""

from django.utils import translation
from django.utils.translation import gettext as _
from django.utils.translation import gettext_noop

TEMPLATES = {
    "expense_submitted": (
        gettext_noop("Expense waiting for approval"),
        gettext_noop("%(actor)s sent ₹%(amount)s paid to %(payee)s for approval."),
    ),
    "expense_approved": (
        gettext_noop("Expense approved"),
        gettext_noop("₹%(amount)s paid to %(payee)s was approved by %(actor)s."),
    ),
    "expense_rejected": (
        gettext_noop("Expense rejected"),
        gettext_noop("₹%(amount)s paid to %(payee)s was rejected by %(actor)s: %(reason)s"),
    ),
    "void_requested": (
        gettext_noop("Receipt void requested"),
        gettext_noop("%(actor)s asked to void receipt %(number)s (₹%(amount)s): %(reason)s"),
    ),
    "void_approved": (
        gettext_noop("Receipt voided"),
        gettext_noop("Your request to void receipt %(number)s was approved by %(actor)s."),
    ),
    "void_rejected": (
        gettext_noop("Void request rejected"),
        gettext_noop("Your request to void receipt %(number)s was rejected by %(actor)s."),
    ),
    "receipt_issued": (
        gettext_noop("Thank you for your contribution"),
        gettext_noop("₹%(amount)s received for %(event)s. Receipt no. %(number)s."),
    ),
    "dues_reminder": (
        gettext_noop("Contribution reminder"),
        gettext_noop("₹%(amount)s is due for %(type)s (%(event)s). Please pay your collector or online."),
    ),
    "online_payment_failed": (
        gettext_noop("Payment not completed"),
        gettext_noop(
            "Your payment of ₹%(amount)s for %(event)s did not go through. Any money deducted will be returned."
        ),
    ),
}


class _Safe(dict):
    def __missing__(self, key):
        return ""


def render(notification, language: str | None = None) -> tuple[str, str]:
    if notification.type == "announcement":  # written by the organization, shown as written
        return notification.params.get("title", ""), notification.params.get("message", "")
    title, body = TEMPLATES.get(notification.type, (notification.type, ""))
    with translation.override(language or translation.get_language()):
        return _(title), _(body) % _Safe(notification.params) if body else ""
