import io
from datetime import date

import pytest
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.organizations import services as org_services
from apps.organizations.models import OrganizationMembership

DEFAULT_PASSWORD = "Str0ng-Passw0rd!"


@pytest.fixture(autouse=True)
def _run_on_commit_immediately(monkeypatch):
    """Tests run inside a transaction that never commits; run on_commit side effects (emails, SMS) inline."""
    from django.db import transaction

    monkeypatch.setattr(transaction, "on_commit", lambda func, using=None, robust=False: func())


@pytest.fixture(autouse=True)
def _clear_cache():
    from django.core.cache import cache

    from apps.accounts.sms import MemorySMSBackend

    cache.clear()
    MemorySMSBackend.outbox.clear()
    yield


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def make_user(db):
    counter = {"n": 0}

    def _make(full_name=None, email=None, mobile=None, password=DEFAULT_PASSWORD, verified=True, **extra):
        counter["n"] += 1
        n = counter["n"]
        if email is None and mobile is None:
            email = f"user{n}@example.com"
        user = User.objects.create_user(
            full_name=full_name or f"User {n}", email=email, mobile=mobile, password=password, **extra
        )
        if verified:
            now = timezone.now()
            user.email_verified_at = now if user.email else None
            user.mobile_verified_at = now if user.mobile else None
            user.save()
        return user

    return _make


@pytest.fixture
def make_org(db, make_user):
    def _make(name="Test Mandal", admin=None, with_fy=True):
        admin = admin or make_user(full_name=f"{name} Admin")
        fy = {"label": "2027–28", "start_date": date(2027, 4, 1), "end_date": date(2028, 3, 31)} if with_fy else None
        org = org_services.create_organization(user=admin, name=name, financial_year=fy)
        org.admin_user = admin
        return org

    return _make


@pytest.fixture
def add_member(db, make_user):
    def _add(org, role_code, user=None):
        user = user or make_user(full_name=f"{role_code} of {org.name}")
        OrganizationMembership.objects.create(organization=org, user=user, role=org_services.system_role(role_code))
        return user

    return _add


@pytest.fixture
def client_for():
    def _client(user, org=None, event=None):
        client = APIClient()
        client.force_authenticate(user=user)
        if org is not None:
            client.credentials(HTTP_X_ORGANIZATION_ID=str(org.pk))
        return client

    return _client


def png_bytes(size=(600, 600), fmt="PNG", color=(200, 30, 30)):
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format=fmt)
    buffer.seek(0)
    return buffer.getvalue()


@pytest.fixture
def png():
    return png_bytes
