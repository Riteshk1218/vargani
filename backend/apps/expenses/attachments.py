"""Expense bills: JPEG, PNG, WebP or PDF, at most 10 MB each and 10 per expense.

The type is detected from the content. Images are decoded and re-encoded (drops metadata and anything that
is not pixels); PDFs are checked for the PDF header and stored as uploaded. Files are only served through
the authenticated API with `Content-Disposition: attachment`.
"""

import io
import re
import uuid

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework.exceptions import ValidationError

from apps.audit import services as audit
from apps.core.exceptions import BusinessRuleViolation, InvalidStateTransition
from apps.organizations.services import FileTooLarge, UnsupportedFile

from .models import Expense, ExpenseAttachment

MAX_BYTES = 10 * 1024 * 1024
MAX_PER_EXPENSE = 10
IMAGE_FORMATS = {"JPEG": ("image/jpeg", "jpg"), "PNG": ("image/png", "png"), "WEBP": ("image/webp", "webp")}


class UnsupportedBill(UnsupportedFile):
    default_detail = gettext_lazy("Upload a JPG, PNG or WEBP image, or a PDF.")


CHANGEABLE = {Expense.Status.DRAFT, Expense.Status.SUBMITTED, Expense.Status.REJECTED}


def _clean_name(name: str, ext: str) -> str:
    stem = re.sub(r"[^\w\-. ]+", "_", (name or "bill").rsplit(".", 1)[0]).strip(" ._")[:80] or "bill"
    return f"{stem}.{ext}"


def _process(upload) -> tuple[bytes, str, str]:
    if upload.size > MAX_BYTES:
        raise FileTooLarge()
    upload.seek(0)
    head = upload.read(5)
    upload.seek(0)
    if head == b"%PDF-":
        return upload.read(), "application/pdf", "pdf"
    try:
        probe = Image.open(upload)
        fmt = probe.format
        probe.verify()
        upload.seek(0)
        image = Image.open(upload)
        image.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise UnsupportedBill() from exc
    if fmt not in IMAGE_FORMATS:
        raise UnsupportedBill()
    content_type, ext = IMAGE_FORMATS[fmt]
    image = ImageOps.exif_transpose(image)
    if fmt == "JPEG":
        image = image.convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, format=fmt, quality=88) if fmt != "PNG" else image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue(), content_type, ext


def add(expense, upload, *, admin=False, request=None, actor=None) -> ExpenseAttachment:
    if expense.status not in CHANGEABLE and not admin:
        raise InvalidStateTransition()
    if upload is None:
        raise ValidationError({"file": [_("Choose a file.")]})
    content, content_type, ext = _process(upload)
    key = None
    try:
        with transaction.atomic():
            expense = Expense.objects.select_for_update().get(pk=expense.pk)
            if expense.attachments.count() >= MAX_PER_EXPENSE:
                raise BusinessRuleViolation(_("An expense can have at most 10 attachments."))
            key = default_storage.save(
                f"orgs/{expense.organization_id}/expenses/{expense.pk}/{uuid.uuid4().hex}.{ext}", ContentFile(content)
            )
            attachment = _create(expense, upload, key, content, content_type, ext, request, actor)
    except Exception:
        if key:
            default_storage.delete(key)  # nothing points at it
        raise
    return attachment


def _create(expense, upload, key, content, content_type, ext, request, actor) -> ExpenseAttachment:
    attachment = ExpenseAttachment.objects.create(
        organization_id=expense.organization_id,
        expense=expense,
        file=key,
        original_name=_clean_name(getattr(upload, "name", ""), ext),
        content_type=content_type,
        size_bytes=len(content),
        created_by=actor,
        updated_by=actor,
    )
    audit.record(
        request=request,
        actor=actor,
        organization=expense.organization,
        action=audit.CREATE,
        entity_type="expenses.expenseattachment",
        entity_id=attachment.pk,
        after={"expense": str(expense.pk), "name": attachment.original_name, "size": attachment.size_bytes},
    )
    return attachment


def remove(attachment, *, admin=False, request=None, actor=None):
    """Only while the expense can still change (an approved expense keeps its bills), unless an admin."""
    with transaction.atomic():
        expense = Expense.objects.select_for_update().get(pk=attachment.expense_id)
        if expense.status not in CHANGEABLE and not admin:
            raise InvalidStateTransition()
        key = attachment.file
        audit.record(
            request=request,
            actor=actor,
            organization=expense.organization,
            action=audit.SOFT_DELETE,
            entity_type="expenses.expenseattachment",
            entity_id=attachment.pk,
            before={"expense": str(expense.pk), "name": attachment.original_name, "file": key},
        )
        attachment.delete()
        transaction.on_commit(lambda: default_storage.delete(key))
