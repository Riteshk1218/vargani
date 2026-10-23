import hashlib
import io
import logging
import secrets
import uuid
from datetime import timedelta

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.forms.models import model_to_dict
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext as _
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError

from apps.audit import services as audit
from apps.core.exceptions import BusinessRuleViolation
from apps.expenses.defaults import seed_categories

from .catalog import ADMIN_ROLE
from .models import FinancialYear, Invitation, Organization, OrganizationMembership, Role

logger = logging.getLogger(__name__)

DEFAULT_SETTINGS = {
    "allow_unassigned_collection": False,
    "require_expense_approval": True,
    "member_portal_enabled": False,
    "auto_reminders": False,
}
SETTINGS_TYPES = {key: type(value) for key, value in DEFAULT_SETTINGS.items()}


def system_role(code: str) -> Role:
    return Role.objects.get(organization__isnull=True, code=code)


def _unique_slug(name: str) -> str:
    base = slugify(name)[:60] or "org"
    return f"{base}-{secrets.token_hex(3)}"


@transaction.atomic
def create_organization(*, user, request=None, financial_year=None, **fields) -> Organization:
    """Create an organization and make its creator the Organization Admin, in one transaction."""
    org = Organization.objects.create(
        slug=_unique_slug(fields.get("name", "")),
        created_by=user,
        settings=dict(DEFAULT_SETTINGS),
        **fields,
    )
    membership = OrganizationMembership.objects.create(organization=org, user=user, role=system_role(ADMIN_ROLE))
    seed_categories(org)
    audit.record(
        request=request,
        actor=user,
        organization=org,
        membership=membership,
        action=audit.CREATE,
        entity_type="organizations.organization",
        entity_id=org.pk,
        after=model_to_dict(org),
    )
    audit.record(
        request=request,
        actor=user,
        organization=org,
        membership=membership,
        action=audit.ROLE_CHANGE,
        entity_type="organizations.organizationmembership",
        entity_id=membership.pk,
        after={"user": str(user.pk), "role": ADMIN_ROLE, "reason": "organization_creator"},
    )
    if financial_year:
        fy = FinancialYear.objects.create(
            organization=org, created_by=user, updated_by=user, is_current=True, **financial_year
        )
        audit.record(
            request=request,
            actor=user,
            organization=org,
            membership=membership,
            action=audit.CREATE,
            entity_type="organizations.financialyear",
            entity_id=fy.pk,
            after=model_to_dict(fy),
        )
    return org


def validate_settings(values: dict) -> dict:
    errors = {}
    for key, value in values.items():
        if key not in SETTINGS_TYPES:
            errors[key] = [_("Unknown setting.")]
        elif not isinstance(value, SETTINGS_TYPES[key]):
            errors[key] = [_("Invalid value.")]
    if errors:
        raise ValidationError(errors)
    return values


# --- Logo ---------------------------------------------------------------------
ALLOWED_LOGO_FORMATS = {"PNG", "JPEG", "WEBP"}
LOGO_MAX_SIDE = 1024
LOGO_MIN_SIDE = 64


class UnsupportedFile(APIException):
    status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    default_detail = _("Upload a PNG, JPG, JPEG or WEBP image.")
    default_code = "unsupported_file_type"


class FileTooLarge(APIException):
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    default_detail = _("The file is too large.")
    default_code = "file_too_large"


def process_logo(upload) -> bytes:
    """Validate by decoding the actual image (not the extension), then re-encode to a clean PNG.

    Re-encoding strips metadata and anything that is not pixel data.
    """
    if upload.size > settings.LOGO_MAX_BYTES:
        raise FileTooLarge()
    try:
        upload.seek(0)
        probe = Image.open(upload)
        image_format = probe.format
        probe.verify()
        upload.seek(0)
        image = Image.open(upload)
        image.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise UnsupportedFile() from exc
    if image_format not in ALLOWED_LOGO_FORMATS:
        raise UnsupportedFile()
    if min(image.size) < LOGO_MIN_SIDE:
        raise ValidationError({"logo": [_("The image is too small. Use at least 512 × 512 pixels.")]})
    image = ImageOps.exif_transpose(image).convert("RGBA")
    image.thumbnail((LOGO_MAX_SIDE, LOGO_MAX_SIDE))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


@transaction.atomic
def set_logo(org: Organization, upload, request) -> Organization:
    content = process_logo(upload)
    old_key = org.logo
    key = default_storage.save(f"orgs/{org.pk}/logo/{uuid.uuid4().hex}.png", ContentFile(content))
    org.logo = key
    org.save(update_fields=["logo", "updated_at"])
    audit.record(
        request=request,
        organization=org,
        action=audit.LOGO_CHANGE,
        entity_type="organizations.organization",
        entity_id=org.pk,
        before={"logo": old_key},
        after={"logo": key},
    )
    if old_key:
        transaction.on_commit(lambda: default_storage.delete(old_key))
    return org


@transaction.atomic
def remove_logo(org: Organization, request) -> Organization:
    old_key = org.logo
    if not old_key:
        return org
    org.logo = ""
    org.save(update_fields=["logo", "updated_at"])
    audit.record(
        request=request,
        organization=org,
        action=audit.LOGO_CHANGE,
        entity_type="organizations.organization",
        entity_id=org.pk,
        before={"logo": old_key},
        after={"logo": ""},
    )
    transaction.on_commit(lambda: default_storage.delete(old_key))
    return org


def logo_url(org: Organization, request=None) -> str | None:
    if not org.logo:
        return None
    url = default_storage.url(org.logo)
    if request is not None and url.startswith("/"):
        return request.build_absolute_uri(url)
    return url


# --- Financial years ------------------------------------------------------------
@transaction.atomic
def set_current_financial_year(fy: FinancialYear, request) -> FinancialYear:
    if fy.status == FinancialYear.Status.CLOSED:
        raise BusinessRuleViolation(_("A closed financial year cannot be made current."))
    previous = FinancialYear.objects.select_for_update().filter(organization=fy.organization, is_current=True)
    previous_ids = [str(p.pk) for p in previous]
    previous.update(is_current=False)
    fy.is_current = True
    fy.updated_by = request.user
    fy.save(update_fields=["is_current", "updated_by", "updated_at"])
    audit.record(
        request=request,
        organization=fy.organization,
        action=audit.STATUS_CHANGE,
        entity_type="organizations.financialyear",
        entity_id=fy.pk,
        before={"current": previous_ids},
        after={"current": str(fy.pk)},
    )
    return fy


@transaction.atomic
def close_financial_year(fy: FinancialYear, request) -> FinancialYear:
    if fy.status == FinancialYear.Status.CLOSED:
        return fy
    fy.status = FinancialYear.Status.CLOSED
    fy.is_current = False
    fy.updated_by = request.user
    fy.save(update_fields=["status", "is_current", "updated_by", "updated_at"])
    audit.record(
        request=request,
        organization=fy.organization,
        action=audit.STATUS_CHANGE,
        entity_type="organizations.financialyear",
        entity_id=fy.pk,
        before={"status": "open"},
        after={"status": "closed"},
    )
    return fy


# --- Members & invitations ------------------------------------------------------
def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def assignable_roles(org: Organization):
    from django.db.models import Q

    return Role.objects.filter(Q(organization__isnull=True) | Q(organization=org))


def _active_admin_count(org: Organization) -> int:
    return OrganizationMembership.objects.filter(
        organization=org, status=OrganizationMembership.Status.ACTIVE, role__code=ADMIN_ROLE
    ).count()


@transaction.atomic
def create_invitation(*, org, role, email, mobile, full_name, request) -> tuple[Invitation, str]:
    from apps.accounts.models import User

    existing_user = None
    if email:
        existing_user = User.objects.filter(email=email).first()
    if existing_user is None and mobile:
        existing_user = User.objects.filter(mobile=mobile).first()
    if (
        existing_user
        and OrganizationMembership.objects.filter(
            organization=org, user=existing_user, status=OrganizationMembership.Status.ACTIVE
        ).exists()
    ):
        raise ValidationError(
            {"non_field_errors": [_("This person already has access to the organization.")]}, code="already_member"
        )

    # Revoke older pending invitations to the same destination so only one link works.
    pending = Invitation.objects.filter(organization=org, status=Invitation.Status.PENDING)
    if email:
        pending.filter(email=email).update(status=Invitation.Status.REVOKED)
    if mobile:
        pending.filter(mobile=mobile).update(status=Invitation.Status.REVOKED)

    token = secrets.token_urlsafe(32)
    invitation = Invitation.objects.create(
        organization=org,
        email=email,
        mobile=mobile,
        full_name=full_name or "",
        role=role,
        token_hash=_hash_token(token),
        expires_at=timezone.now() + timedelta(days=settings.INVITATION_TTL_DAYS),
        created_by=request.user,
        updated_by=request.user,
    )
    audit.record(
        request=request,
        organization=org,
        action=audit.INVITE,
        entity_type="organizations.invitation",
        entity_id=invitation.pk,
        after={"email": email, "mobile": mobile, "role": role.code},
    )
    return invitation, token


def send_invitation_email(invitation: Invitation, token: str) -> bool:
    """Email the invitation link. Returns False if the mail provider refused it, so the admin can share the
    link another way (it is shown once after creating the invitation)."""
    from apps.accounts.tasks import send_email

    org = invitation.organization
    message = _("You have been invited to join %(org)s as %(role)s. Open this link to accept: %(link)s") % {
        "org": org.name,
        "role": invitation.role.name,
        "link": invitation_link(token),
    }
    try:
        send_email.delay(_("Invitation to %(org)s") % {"org": org.name}, message, invitation.email)
    except Exception:
        logger.exception("Could not send invitation %s by email", invitation.pk)
        return False
    return True


def invitation_link(token: str) -> str:
    return f"{settings.FRONTEND_URL.rstrip('/')}/invite/{token}"


def find_invitation(token: str) -> Invitation | None:
    invitation = Invitation.objects.select_related("organization", "role").filter(token_hash=_hash_token(token)).first()
    if invitation and invitation.status == Invitation.Status.PENDING and invitation.expires_at < timezone.now():
        invitation.status = Invitation.Status.EXPIRED
        invitation.save(update_fields=["status", "updated_at"])
    return invitation


@transaction.atomic
def accept_invitation(*, token, user, request) -> OrganizationMembership:
    invitation = find_invitation(token)
    if invitation is None or invitation.status != Invitation.Status.PENDING:
        raise ValidationError({"token": [_("This invitation is invalid or has expired.")]}, code="invalid_invitation")
    invitation = Invitation.objects.select_for_update().get(pk=invitation.pk)
    # The invitation must be accepted by the person it was sent to (a verified matching identifier).
    email_match = bool(invitation.email and user.email == invitation.email and user.email_verified_at)
    mobile_match = bool(invitation.mobile and user.mobile == invitation.mobile and user.mobile_verified_at)
    if not (email_match or mobile_match):
        raise ValidationError(
            {"token": [_("This invitation was sent to a different email or mobile number.")]},
            code="invitation_identity_mismatch",
        )
    membership, created = OrganizationMembership.objects.get_or_create(
        organization=invitation.organization,
        user=user,
        defaults={"role": invitation.role, "invited_by": invitation.created_by},
    )
    if not created:
        if membership.status == OrganizationMembership.Status.ACTIVE:
            raise ValidationError({"token": [_("You already have access to this organization.")]})
        membership.role = invitation.role
        membership.status = OrganizationMembership.Status.ACTIVE
        membership.save(update_fields=["role", "status", "updated_at"])
    invitation.status = Invitation.Status.ACCEPTED
    invitation.accepted_by = user
    invitation.accepted_at = timezone.now()
    invitation.save(update_fields=["status", "accepted_by", "accepted_at", "updated_at"])
    audit.record(
        request=request,
        actor=user,
        organization=invitation.organization,
        membership=membership,
        action=audit.INVITE_ACCEPT,
        entity_type="organizations.organizationmembership",
        entity_id=membership.pk,
        after={"user": str(user.pk), "role": invitation.role.code},
    )
    return membership


@transaction.atomic
def revoke_invitation(invitation: Invitation, request) -> Invitation:
    if invitation.status != Invitation.Status.PENDING:
        from apps.core.exceptions import InvalidStateTransition

        raise InvalidStateTransition()
    invitation.status = Invitation.Status.REVOKED
    invitation.updated_by = request.user
    invitation.save(update_fields=["status", "updated_by", "updated_at"])
    audit.record(
        request=request,
        organization=invitation.organization,
        action=audit.INVITE_REVOKE,
        entity_type="organizations.invitation",
        entity_id=invitation.pk,
    )
    return invitation


UNCHANGED = object()


@transaction.atomic
def update_membership(
    membership: OrganizationMembership, *, role=None, status_value=None, can_download=UNCHANGED, request
):
    membership = OrganizationMembership.objects.select_for_update().select_related("role").get(pk=membership.pk)
    org = membership.organization
    before = {"role": membership.role.code, "status": membership.status, "can_download": membership.can_download}
    losing_admin = (
        membership.role.code == ADMIN_ROLE
        and membership.status == OrganizationMembership.Status.ACTIVE
        and (
            (role is not None and role.code != ADMIN_ROLE)
            or (status_value is not None and status_value != OrganizationMembership.Status.ACTIVE)
        )
    )
    if losing_admin and _active_admin_count(org) <= 1:
        raise BusinessRuleViolation(_("The organization must keep at least one active Organization Admin."))
    if role is not None:
        membership.role = role
    if status_value is not None:
        membership.status = status_value
    if can_download is not UNCHANGED:
        membership.can_download = can_download
    membership.save(update_fields=["role", "status", "can_download", "updated_at"])
    after = {"role": membership.role.code, "status": membership.status, "can_download": membership.can_download}
    if before != after:
        audit.record(
            request=request,
            organization=org,
            action=audit.ROLE_CHANGE,
            entity_type="organizations.organizationmembership",
            entity_id=membership.pk,
            before=before,
            after=after,
        )
    return membership


# --- Users added directly by an admin -------------------------------------------
def _find_existing_user(email, mobile):
    from apps.accounts.models import User

    matches = {}
    if email:
        matches.update({u.pk: u for u in User.objects.filter(email__iexact=email)})
    if mobile:
        matches.update({u.pk: u for u in User.objects.filter(mobile=mobile)})
    if len(matches) > 1:
        raise ValidationError(
            {"non_field_errors": [_("This email and this mobile number belong to two different accounts.")]},
            code="identity_conflict",
        )
    return next(iter(matches.values()), None)


def create_login(*, full_name, email, mobile, password):
    """A new login whose details the admin typed in. Returns (user, created): an existing account is reused
    and keeps its own password."""
    from apps.accounts.models import User

    existing = _find_existing_user(email, mobile)
    if existing is not None and existing.is_verified:
        return existing, False
    if existing is not None:
        # Someone started signing up but never entered the code, so nobody has proved the account is theirs
        # (a new sign-up may take it over the same way). The admin's details replace it.
        user = existing
        user.full_name = full_name
        user.email = email or user.email
        user.mobile = mobile or user.mobile
        user.set_password(password)
        user.save()
    else:
        user = User.objects.create_user(full_name=full_name, email=email, mobile=mobile, password=password)
    # The admin vouches for these details, so the person can log in straight away.
    now = timezone.now()
    user.email_verified_at = now if user.email else None
    user.mobile_verified_at = now if user.mobile else None
    user.save(update_fields=["email_verified_at", "mobile_verified_at"])
    return user, True


@transaction.atomic
def add_member_directly(*, org, role, full_name, email, mobile, password, request):
    """Give someone access without an invitation link: the admin sets their login details."""
    user, created = create_login(full_name=full_name, email=email, mobile=mobile, password=password)
    membership = OrganizationMembership.objects.filter(organization=org, user=user).first()
    if membership is not None and membership.status == OrganizationMembership.Status.ACTIVE:
        raise ValidationError(
            {"non_field_errors": [_("This person already has access to the organization.")]}, code="already_member"
        )
    if membership is None:
        membership = OrganizationMembership.objects.create(
            organization=org, user=user, role=role, invited_by=request.user
        )
    else:
        membership.role = role
        membership.status = OrganizationMembership.Status.ACTIVE
        membership.save(update_fields=["role", "status", "updated_at"])
    # Any open invitation for the same person is no longer needed.
    pending = Invitation.objects.filter(organization=org, status=Invitation.Status.PENDING)
    if user.email:
        pending.filter(email=user.email).update(status=Invitation.Status.REVOKED)
    if user.mobile:
        pending.filter(mobile=user.mobile).update(status=Invitation.Status.REVOKED)
    audit.record(
        request=request,
        organization=org,
        action=audit.ROLE_CHANGE,
        entity_type="organizations.organizationmembership",
        entity_id=membership.pk,
        after={"user": str(user.pk), "role": role.code, "reason": "added_by_admin", "new_login": created},
    )
    return membership, created


def can_admin_reset_password(membership: OrganizationMembership) -> bool:
    """An organization admin may set the password only of a login that belongs to their organization alone,
    so they can never take over an account someone also uses elsewhere."""
    from apps.core.rls import unscoped

    user = membership.user
    if user.is_platform_admin or user.is_staff:
        return False
    # Row-level security hides other organizations' memberships during a request, so look past it here.
    with unscoped():
        return not (
            OrganizationMembership.objects.filter(user=user).exclude(organization=membership.organization).exists()
        )


@transaction.atomic
def set_member_password(membership: OrganizationMembership, password: str, request):
    from apps.accounts.services import revoke_all_tokens

    if membership.user_id == request.user.pk:
        raise BusinessRuleViolation(_("Change your own password from My profile."))
    if not can_admin_reset_password(membership):
        raise BusinessRuleViolation(
            _("This person also uses Vargani with another organization. They can reset it with Forgot password.")
        )
    user = membership.user
    user.set_password(password)
    user.save(update_fields=["password"])
    revoke_all_tokens(user)
    audit.record(
        request=request,
        organization=membership.organization,
        action=audit.PASSWORD_CHANGE,
        entity_type="accounts.user",
        entity_id=user.pk,
        after={"reason": "set_by_admin", "membership": str(membership.pk)},
    )
