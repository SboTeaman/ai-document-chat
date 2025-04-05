import pytest
from django.test import override_settings
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestMiddleware:
    def test_request_id_header_present(self):
        resp = APIClient().get("/health/")
        assert resp["X-Request-ID"]

    def test_security_headers_present(self):
        resp = APIClient().get("/health/")
        assert resp["X-Content-Type-Options"] == "nosniff"
        assert resp["X-Frame-Options"] == "DENY"

    @override_settings(CONTENT_SECURITY_POLICY="default-src 'self'")
    def test_csp_header_set_when_configured(self):
        resp = APIClient().get("/health/")
        assert resp["Content-Security-Policy"] == "default-src 'self'"
