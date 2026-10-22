"""Serving the website and public logos from Django, for single-service hosting without nginx
(WEBSITE_DIR set, see docs/deploy/RENDER.md). Mirrors deploy/nginx.conf."""

from pathlib import Path

from django.conf import settings
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404, HttpResponse

# Same policy nginx sends with the website (deploy/nginx.conf).
WEBSITE_CSP = (
    "default-src 'self'; script-src 'self' https://checkout.razorpay.com; "
    "frame-src https://api.razorpay.com https://checkout.razorpay.com; "
    "connect-src 'self' https://api.razorpay.com https://lumberjack.razorpay.com; img-src 'self' data: blob: https:; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; "
    "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
)
WEBSITE_PERMISSIONS = 'camera=(), microphone=(), geolocation=(), payment=(self "https://checkout.razorpay.com")'


def index(request, path=""):
    """Every website path returns index.html; React Router takes over in the browser."""
    page = Path(settings.WEBSITE_DIR) / "index.html"
    if not page.is_file():
        raise Http404()
    response = HttpResponse(page.read_bytes(), content_type="text/html; charset=utf-8")
    response["Cache-Control"] = "no-cache"  # new releases load at once
    response["Content-Security-Policy"] = WEBSITE_CSP
    response["Permissions-Policy"] = WEBSITE_PERMISSIONS
    return response


def logo(request, org_id, filename):
    """Organization logos are the only public uploads (receipts and shared links show them)."""
    name = f"orgs/{org_id}/logo/{filename}"
    try:
        handle = default_storage.open(name)
    except FileNotFoundError as exc:
        raise Http404() from exc
    response = FileResponse(handle, content_type="image/png")
    response["Cache-Control"] = "public, max-age=604800"
    response["X-Content-Type-Options"] = "nosniff"
    return response
