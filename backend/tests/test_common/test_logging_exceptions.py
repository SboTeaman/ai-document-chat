import json
import logging
import sys
from unittest.mock import patch

from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response

from common.exceptions import ServiceError, custom_exception_handler
from common.logging import JSONFormatter, get_request_id, set_request_id


class TestRequestId:
    def test_set_and_get(self):
        set_request_id("abc-123")
        assert get_request_id() == "abc-123"


class TestJSONFormatter:
    def test_includes_message_and_request_id(self):
        set_request_id("rid")
        record = logging.LogRecord("app", logging.INFO, "p", 1, "hello %s", ("world",), None)
        out = json.loads(JSONFormatter().format(record))
        assert out["message"] == "hello world"
        assert out["request_id"] == "rid"

    def test_redacts_sensitive_extra_keeps_safe(self):
        record = logging.LogRecord("app", logging.INFO, "p", 1, "m", (), None)
        record.workspace_id = 5
        record.password = "secret"
        out = json.loads(JSONFormatter().format(record))
        assert out["extra"]["workspace_id"] == 5
        assert "password" not in out.get("extra", {})

    def test_serialises_exception(self):
        try:
            raise ValueError("boom")
        except ValueError:
            record = logging.LogRecord("app", logging.ERROR, "p", 1, "m", (), sys.exc_info())
        out = json.loads(JSONFormatter().format(record))
        assert "ValueError" in out["exception"]


class TestServiceError:
    def test_stores_message_and_code(self):
        err = ServiceError("nope", code="bad")
        assert err.message == "nope"
        assert err.code == "bad"
        assert str(err) == "nope"


class TestExceptionHandler:
    def test_http404_mapped_to_404(self):
        resp = custom_exception_handler(Http404(), {})
        assert resp.status_code == 404
        assert resp.data["errors"][0]["message"] == "Not found."

    def test_permission_denied_mapped_to_403(self):
        resp = custom_exception_handler(PermissionDenied(), {})
        assert resp.status_code == 403

    def test_unhandled_exception_returns_none(self):
        assert custom_exception_handler(ValueError("x"), {}) is None

    def test_validation_dict_with_field_lists(self):
        resp = custom_exception_handler(ValidationError({"email": ["required"]}), {})
        assert resp.data["errors"][0] == {"code": "email", "message": "required", "field": "email"}

    def test_single_detail_dict_becomes_top_level(self):
        with patch("common.exceptions.exception_handler", return_value=Response({"detail": "oops"}, status=400)):
            resp = custom_exception_handler(APIException(), {})
        assert resp.data["errors"][0] == {"code": "error", "message": "oops", "field": None}

    def test_dict_with_scalar_value(self):
        with patch("common.exceptions.exception_handler", return_value=Response({"name": "bad"}, status=400)):
            resp = custom_exception_handler(APIException(), {})
        assert resp.data["errors"][0] == {"code": "name", "message": "bad", "field": "name"}

    def test_list_detail(self):
        with patch("common.exceptions.exception_handler", return_value=Response(["a", "b"], status=400)):
            resp = custom_exception_handler(APIException(), {})
        assert [e["message"] for e in resp.data["errors"]] == ["a", "b"]

    def test_scalar_detail(self):
        with patch("common.exceptions.exception_handler", return_value=Response("plain", status=400)):
            resp = custom_exception_handler(APIException(), {})
        assert resp.data["errors"][0] == {"code": "error", "message": "plain", "field": None}
