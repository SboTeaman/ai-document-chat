import uuid
from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse

from common.logging import set_request_id


class RequestIDMiddleware:
    """Assigns a UUID to every request, exposes it on the request and in
    thread-local storage (for logs), and echoes it back as ``X-Request-ID``."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Generate the request ID, process the request, and tag the response."""
        request_id = str(uuid.uuid4())
        request.request_id = request_id  # type: ignore[attr-defined]
        set_request_id(request_id)

        response = self.get_response(request)
        response["X-Request-ID"] = request_id
        return response


class SecurityHeadersMiddleware:
    """Adds hardening headers (nosniff, frame-deny, referrer, permissions) and a
    Content-Security-Policy when one is configured, to every response."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Attach the security headers to the downstream response."""
        response = self.get_response(request)
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "DENY"
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        csp = getattr(settings, "CONTENT_SECURITY_POLICY", "")
        if csp:
            response["Content-Security-Policy"] = csp
        return response
