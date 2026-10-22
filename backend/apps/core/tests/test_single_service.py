"""Single-service hosting (Dockerfile.render): files in PostgreSQL, website and logos served by Django."""

import importlib

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import clear_url_caches
from PIL import Image

from apps.core.models import StoredFile
from config import dburl

DB_STORAGES = {
    "default": {"BACKEND": "apps.core.storage.DatabaseStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@pytest.fixture
def single_service(settings, tmp_path):
    """Database storage plus a built website, with the URLs reloaded for those settings."""
    (tmp_path / "index.html").write_text("<!doctype html><title>Vargani</title>")
    settings.STORAGE_BACKEND = "database"
    settings.WEBSITE_DIR = str(tmp_path)
    with override_settings(STORAGES=DB_STORAGES):
        import config.urls

        importlib.reload(config.urls)
        clear_url_caches()
        yield
    settings.STORAGE_BACKEND = "local"
    settings.WEBSITE_DIR = ""
    importlib.reload(config.urls)
    clear_url_caches()


@pytest.mark.django_db
def test_database_storage_round_trip(single_service):
    name = default_storage.save("orgs/x/reports/a.csv", ContentFile(b"amount\n500\n"))
    assert default_storage.exists(name) and default_storage.size(name) == 11
    with default_storage.open(name) as handle:
        assert handle.read() == b"amount\n500\n"
    second = default_storage.save("orgs/x/reports/a.csv", ContentFile(b"other"))
    assert second != name  # never overwrites
    default_storage.delete(name)
    assert not default_storage.exists(name) and StoredFile.objects.count() == 1


@pytest.mark.django_db
def test_logo_is_public_but_bills_are_not(single_service, api, client_for, make_org, png):
    org = make_org()
    client = client_for(org.admin_user, org)
    upload = SimpleUploadedFile("logo.png", png(), content_type="image/png")
    assert client.put(f"/api/v1/organizations/{org.pk}/logo/", {"logo": upload}, format="multipart").status_code == 200
    org.refresh_from_db()
    response = api.get(f"/media/{org.logo}")
    assert response.status_code == 200 and response["Content-Type"] == "image/png"
    assert b"".join(response.streaming_content).startswith(b"\x89PNG")
    default_storage.save(f"orgs/{org.pk}/expenses/e/bill.png", ContentFile(png()))
    assert api.get(f"/media/orgs/{org.pk}/expenses/e/bill.png").status_code == 404


@pytest.mark.django_db
def test_website_pages_return_the_app_and_api_stays_json(single_service, api):
    page = api.get("/collect/new")
    assert page.status_code == 200 and b"<title>Vargani</title>" in page.content
    assert "script-src 'self'" in page["Content-Security-Policy"]
    assert api.get("/api/v1/health/").json() == {"status": "ok"}
    assert api.get("/api/v1/no-such-endpoint/").status_code == 404


def test_bill_photos_are_scaled_down(png):
    from apps.expenses.attachments import MAX_SIDE, _process

    content, content_type, _ext = _process(SimpleUploadedFile("bill.jpg", png(size=(4000, 3000), fmt="JPEG")))
    image = Image.open(ContentFile(content))
    assert content_type == "image/jpeg" and max(image.size) == MAX_SIDE


def test_app_database_url_from_owner_url():
    admin = "postgresql://neondb_owner:s3cret@ep-cool-1234-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
    url = dburl.app_url(admin, "vargani_app", "key")
    assert url == (
        f"postgresql://vargani_app:{dburl.app_role_password('key')}"
        "@ep-cool-1234.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
    )
    assert dburl.app_role_password("key") != dburl.app_role_password("other")


def test_platform_generated_encryption_key_is_accepted(settings):
    from apps.gateway import crypto

    settings.FIELD_ENCRYPTION_KEY = "q8V+3n/generated-by-render=="
    assert crypto.decrypt(crypto.encrypt("rzp_secret")) == "rzp_secret"
