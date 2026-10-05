"""Consistent error envelope for every non-2xx API response.

{"error": {"code": "...", "message": "...", "details": {...}}, "request_id": "..."}
"""

import logging

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.http import Http404
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from .context import get_request_id

logger = logging.getLogger(__name__)


class OrganizationRequired(exceptions.APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("Select an organization (X-Organization-ID header).")
    default_code = "organization_required"


class NotAMember(exceptions.APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _("You are not a member of this organization.")
    default_code = "not_a_member"


class EventRequired(exceptions.APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("Select an event (event parameter).")
    default_code = "event_required"


class Conflict(exceptions.APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = _("This conflicts with existing data.")
    default_code = "conflict"


class InvalidStateTransition(exceptions.APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = _("This action is not allowed in the record's current state.")
    default_code = "invalid_state_transition"


class BusinessRuleViolation(exceptions.APIException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = _("This request breaks a business rule.")
    default_code = "business_rule_violation"


_STATUS_CODES = {
    400: "validation_error",
    401: "authentication_failed",
    403: "permission_denied",
    404: "not_found",
    405: "method_not_allowed",
    406: "not_acceptable",
    409: "conflict",
    413: "file_too_large",
    415: "unsupported_media_type",
    422: "business_rule_violation",
    429: "throttled",
}

_GENERIC_MESSAGES = {
    "validation_error": _("Some fields are invalid."),
    "not_found": _("Not found."),
}


def _details_from(data):
    """Turn DRF's get_full_details() output into {field: [{code, message}]}."""
    if isinstance(data, dict):
        if set(data.keys()) == {"message", "code"}:
            return [{"code": data["code"], "message": str(data["message"])}]
        return {key: _details_from(value) for key, value in data.items()}
    if isinstance(data, list):
        flattened = []
        for item in data:
            converted = _details_from(item)
            if isinstance(converted, list):
                flattened.extend(converted)
            else:
                flattened.append(converted)
        return flattened
    return [{"code": "invalid", "message": str(data)}]


def api_exception_handler(exc, context):
    if isinstance(exc, DjangoValidationError):
        exc = exceptions.ValidationError(exc.message_dict if hasattr(exc, "error_dict") else exc.messages)
    elif isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = exceptions.PermissionDenied()
    elif isinstance(exc, IntegrityError):
        # Database constraints are the last line of defence; report a conflict instead of a 500.
        logger.warning("Integrity error", exc_info=exc)
        exc = Conflict()

    response = exception_handler(exc, context)
    if response is None:
        logger.exception("Unhandled API error", extra={"request_id": get_request_id()})
        return Response(
            {
                "error": {
                    "code": "server_error",
                    "message": str(_("Something went wrong. Please try again.")),
                    "details": {},
                },
                "request_id": get_request_id(),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(exc, exceptions.ValidationError):
        code = "validation_error"
        details = _details_from(exc.get_full_details())
        if isinstance(details, list):
            details = {"non_field_errors": details}
        message = str(_GENERIC_MESSAGES[code])
        if set(details.keys()) == {"non_field_errors"} and details["non_field_errors"]:
            message = details["non_field_errors"][0]["message"]
    else:
        full = exc.get_full_details() if isinstance(exc, exceptions.APIException) else {}
        code = full.get("code") if isinstance(full, dict) else None
        if not code or code in ("error", "invalid"):
            code = _STATUS_CODES.get(response.status_code, "error")
        if isinstance(exc, exceptions.NotAuthenticated):
            code = "not_authenticated"
        message = str(full.get("message")) if isinstance(full, dict) and full.get("message") else str(exc)
        details = {}
        if isinstance(response.data, dict) and "messages" in response.data:  # simplejwt token errors
            code = "token_not_valid"

    response.data = {"error": {"code": code, "message": message, "details": details}, "request_id": get_request_id()}
    return response
