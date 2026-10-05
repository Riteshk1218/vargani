"""Linking a login (User) to a Person record, which is what the member portal shows.

Linking is explicit: an admin links them, or the system links automatically only when exactly one active
Person in an organization has the user's verified mobile number and that organization has the member
portal switched on. Shared family phones are common, so an ambiguous match is never linked.
"""

from django.db import transaction
from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError

from apps.audit import services as audit
from apps.organizations.models import Organization, OrganizationMembership
from apps.organizations.services import system_role
from apps.people.models import Person

LINK = "portal_link"
UNLINK = "portal_unlink"


def portal_enabled(org) -> bool:
    return bool(org.settings.get("member_portal_enabled"))


def _ensure_membership(org, user, *, request=None, actor=None):
    membership = OrganizationMembership.objects.filter(organization=org, user=user).first()
    if membership is None:
        membership = OrganizationMembership.objects.create(organization=org, user=user, role=system_role("member"))
        audit.record(
            request=request,
            actor=actor or user,
            organization=org,
            action=audit.ROLE_CHANGE,
            entity_type="organizations.organizationmembership",
            entity_id=membership.pk,
            after={"user": str(user.pk), "role": "member", "reason": "member_portal"},
        )
    return membership


@transaction.atomic
def link(person, user, *, request=None, actor=None):
    if person.user_id == user.pk:
        return person
    if person.user_id is not None:
        raise ValidationError({"user": [_("This person is already linked to another login. Unlink it first.")]})
    if Person.objects.filter(organization_id=person.organization_id, user=user).exists():
        raise ValidationError({"user": [_("This login is already linked to another person here.")]})
    person.user = user
    person.save(update_fields=["user", "updated_at"])
    _ensure_membership(person.organization, user, request=request, actor=actor)
    audit.record(
        request=request,
        actor=actor,
        organization=person.organization,
        action=LINK,
        entity_type="people.person",
        entity_id=person.pk,
        after={"user": str(user.pk)},
    )
    return person


@transaction.atomic
def unlink(person, *, request=None, actor=None):
    if person.user_id is None:
        return person
    before = {"user": str(person.user_id)}
    person.user = None
    person.save(update_fields=["user", "updated_at"])
    audit.record(
        request=request,
        actor=actor,
        organization=person.organization,
        action=UNLINK,
        entity_type="people.person",
        entity_id=person.pk,
        before=before,
    )
    return person


def eligible_people(mobile):
    """Active people with this mobile in organizations that have the member portal switched on."""
    return Person.objects.filter(
        mobile=mobile,
        is_active=True,
        deleted_at__isnull=True,
        organization__status=Organization.Status.ACTIVE,
        organization__settings__member_portal_enabled=True,
    ).select_related("organization")


def auto_link(user, *, request=None):
    """After a verified mobile login: link wherever exactly one unlinked person has this number."""
    if not user.mobile or user.mobile_verified_at is None:
        return []
    linked = []
    by_org = {}
    for person in eligible_people(user.mobile):
        by_org.setdefault(person.organization_id, []).append(person)
    for people in by_org.values():
        if len(people) != 1:
            continue  # ambiguous (e.g. a family phone): an admin links it by hand
        person = people[0]
        if person.user_id is not None:
            continue
        if Person.objects.filter(organization_id=person.organization_id, user=user).exists():
            continue
        linked.append(link(person, user, request=request, actor=user))
    return linked
