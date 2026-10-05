import uuid

from apps.core.context import set_request_id


class RequestIDMiddleware:
    """Attach a request id to every request/response for log correlation and error reports."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = request.META.get("HTTP_X_REQUEST_ID", "")
        request_id = incoming if 8 <= len(incoming) <= 64 and incoming.replace("-", "").isalnum() else uuid.uuid4().hex
        request.request_id = request_id
        set_request_id(request_id)
        response = self.get_response(request)
        response["X-Request-ID"] = request_id
        return response
