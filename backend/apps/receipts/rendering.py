"""Receipt PDF, public share links and WhatsApp text."""

import hashlib
import secrets
from datetime import date, datetime, timedelta
from decimal import Decimal
from urllib.parse import quote
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone, translation
from django.utils.translation import gettext as _
from django.utils.translation import gettext_noop

from apps.audit import services as audit
from apps.core.money import indian_format
from apps.core.pdf import render_pdf, storage_data_uri
from apps.core.words import rupees_in_words

from .models import Receipt, ReceiptShare

SHARE_DAYS = 180
RECEIPT_SHARE = "receipt_share"

MODE_LABELS = {
    "cash": gettext_noop("Cash"),
    "upi": gettext_noop("UPI"),
    "bank_transfer": gettext_noop("Bank transfer"),
    "cheque": gettext_noop("Cheque"),
    "online": gettext_noop("Online"),
    "other": gettext_noop("Other"),
}


def local_time(moment: datetime, tz_name: str | None) -> datetime:
    """The moment in the organization's time zone (the server runs in UTC)."""
    try:
        return timezone.localtime(moment, ZoneInfo(tz_name or "Asia/Kolkata"))
    except Exception:  # noqa: BLE001
        return timezone.localtime(moment)


def _money(value: str) -> str:
    return indian_format(value)


LANGUAGES = ("en", "mr", "hi")


def receipt_language(receipt: Receipt, requested: str | None = None) -> str:
    """The language asked for (en, mr or hi), else the one the receipt was issued in."""
    return requested if requested in LANGUAGES else (receipt.language or "en")


def signatory(snapshot: dict) -> str | None:
    """The name printed above "Authorised signatory". Receipts issued before it was stored use the collector."""
    return snapshot.get("signatory") or snapshot.get("collector")


def receipt_pdf(receipt: Receipt, language: str | None = None) -> bytes:
    language = receipt_language(receipt, language)
    s = receipt.snapshot
    with translation.override(language):
        lines = [
            {
                "contribution_type": line["contribution_type"],
                "fund": line.get("fund"),
                "month": date.fromisoformat(line["period_month"]) if line.get("period_month") else None,
                "amount": _money(line["amount"]),
                "towards_balance": line.get("towards_balance", False),
            }
            for line in s["lines"]
        ]
        balance = [
            {
                "contribution_type": line["contribution_type"],
                "month": date.fromisoformat(line["period_month"]) if line.get("period_month") else None,
                "amount": _money(line["amount"]),
            }
            for line in s.get("balance_lines", [])
        ]
        context = {
            "balance": balance,
            "balance_total": _money(s.get("balance_total") or "0"),
            "receipt": receipt,
            "s": {**s, "total": _money(s["total"])},
            "lines": lines,
            "language": language,
            "logo": storage_data_uri(s["organization"].get("logo")),
            "paid_at": local_time(
                datetime.fromisoformat(s["paid_at"]), s.get("timezone") or receipt.organization.timezone
            ),
            "mode": s.get("mode_label") or _(MODE_LABELS.get(s["mode"], s["mode"])),
            "words": rupees_in_words(s["total"]) if language == "en" else "",
            "signatory": signatory(s),
        }
        return render_pdf("receipts/receipt_pdf.html", context)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_share(receipt: Receipt, *, language=None, request=None, actor=None) -> dict:
    token = secrets.token_urlsafe(24)
    share = ReceiptShare.objects.create(
        organization_id=receipt.organization_id,
        receipt=receipt,
        token_hash=_hash(token),
        expires_at=timezone.now() + timedelta(days=SHARE_DAYS),
        created_by=actor,
        updated_by=actor,
    )
    audit.record(
        request=request,
        actor=actor,
        organization=receipt.organization,
        action=RECEIPT_SHARE,
        entity_type="receipts.receipt",
        entity_id=receipt.pk,
        after={"share": str(share.pk), "expires_at": share.expires_at.isoformat()},
    )
    share_url = f"{settings.FRONTEND_URL.rstrip('/')}/r/{token}"
    s = receipt.snapshot
    with translation.override(receipt_language(receipt, language)):
        text = _(
            "Namaskar %(name)s, thank you for your contribution of Rs %(amount)s to %(organization)s "
            "(%(event)s). Receipt no. %(number)s: %(url)s"
        ) % {
            "name": _("Anonymous") if s["person"].get("anonymous") else s["person"]["name"],
            "amount": _money(s["total"]),
            "organization": s["organization"]["name"],
            "event": s["event"]["name"],
            "number": receipt.receipt_number,
            "url": share_url,
        }
        if Decimal(s.get("balance_total") or "0") > 0:
            text += " " + _("Balance due: Rs %(amount)s.") % {"amount": _money(s["balance_total"])}
    digits = "".join(ch for ch in (s["person"].get("mobile") or "") if ch.isdigit())
    whatsapp_url = f"https://wa.me/{digits}?text={quote(text)}" if digits else f"https://wa.me/?text={quote(text)}"
    return {"share_url": share_url, "expires_at": share.expires_at, "whatsapp_text": text, "whatsapp_url": whatsapp_url}


def find_share(token: str) -> ReceiptShare | None:
    share = (
        ReceiptShare.objects.select_related("receipt", "receipt__organization")
        .filter(token_hash=_hash(token), revoked_at__isnull=True, expires_at__gt=timezone.now())
        .first()
    )
    if share is not None:
        ReceiptShare.objects.filter(pk=share.pk).update(view_count=share.view_count + 1)
    return share
