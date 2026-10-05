"""PDF rendering with WeasyPrint. Noto fonts are bundled so Marathi and Hindi (Devanagari) shape correctly."""

import base64
import mimetypes
from pathlib import Path

from django.conf import settings
from django.core.files.storage import default_storage
from django.template.loader import render_to_string

FONT_DIR = Path(settings.BASE_DIR) / "assets" / "fonts"

FONT_CSS = "\n".join(
    f"@font-face {{ font-family: '{family}'; src: url('{(FONT_DIR / file).as_uri()}'); font-weight: {weight}; }}"
    for family, file, weight in [
        ("Noto Sans", "NotoSans-Regular.ttf", 400),
        ("Noto Sans", "NotoSans-Bold.ttf", 700),
        ("Noto Sans Devanagari", "NotoSansDevanagari-Regular.ttf", 400),
        ("Noto Sans Devanagari", "NotoSansDevanagari-Bold.ttf", 700),
    ]
)


def storage_data_uri(key: str | None) -> str | None:
    """Embed a stored file (e.g. the organization logo) so rendering never fetches URLs."""
    if not key:
        return None
    try:
        with default_storage.open(key) as handle:
            data = handle.read()
    except Exception:  # noqa: BLE001 - a missing logo must not block a receipt
        return None
    mime = mimetypes.guess_type(key)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def _no_network(url, *args, **kwargs):
    from weasyprint import default_url_fetcher

    if url.startswith(("file:", "data:")):
        return default_url_fetcher(url, *args, **kwargs)
    raise ValueError("External resources are not allowed in PDFs")


def render_pdf(template: str, context: dict) -> bytes:
    from weasyprint import HTML

    html = render_to_string(template, {**context, "font_css": FONT_CSS})
    return HTML(string=html, base_url=str(FONT_DIR), url_fetcher=_no_network).write_pdf()
