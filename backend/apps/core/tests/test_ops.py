import json
import logging

from django.http import JsonResponse
from django.test import RequestFactory

from apps.core.context import set_request_id
from apps.core.logging import JSONFormatter
from apps.core.security import API_CSP, SecurityHeadersMiddleware


def test_json_log_lines_carry_the_request_id_and_extra_fields():
    set_request_id("abc123def456")
    try:
        record = logging.makeLogRecord(
            {"name": "apps.payments", "levelname": "WARNING", "msg": "payment %s failed", "args": ("P1",), "org": "o1"}
        )
        line = json.loads(JSONFormatter().format(record))
    finally:
        set_request_id(None)
    assert line["message"] == "payment P1 failed"
    assert line["request_id"] == "abc123def456"
    assert line["level"] == "WARNING" and line["org"] == "o1"


def test_api_responses_get_strict_security_headers():
    middleware = SecurityHeadersMiddleware(lambda request: JsonResponse({"ok": True}))
    response = middleware(RequestFactory().get("/api/v1/people/"))
    assert response["Content-Security-Policy"] == API_CSP
    assert response["Cache-Control"] == "no-store"
    other = middleware(RequestFactory().get("/django-admin/"))
    assert not other.has_header("Content-Security-Policy")
