import logging

from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """Normalise every DRF/Django error into a uniform ``{"errors": [...]}`` body.

    Maps Http404/PermissionDenied to API exceptions, then flattens DRF's
    detail (dict, list, or scalar) into a list of ``{code, message, field}``
    objects so the frontend always parses one shape.
    """
    if isinstance(exc, Http404):
        exc = APIException()
        exc.status_code = status.HTTP_404_NOT_FOUND
        exc.detail = "Not found."

    if isinstance(exc, PermissionDenied):
        exc = APIException()
        exc.status_code = status.HTTP_403_FORBIDDEN
        exc.detail = "Permission denied."

    response = exception_handler(exc, context)

    if response is not None:
        errors = []
        detail = response.data

        if isinstance(detail, dict):
            # DRF wraps single-message errors as {"detail": "..."} — treat as top-level, field=null
            if list(detail.keys()) == ["detail"]:
                errors.append({"code": "error", "message": str(detail["detail"]), "field": None})
            else:
                for field, messages in detail.items():
                    if isinstance(messages, list):
                        for msg in messages:
                            errors.append({"code": field, "message": str(msg), "field": field})
                    else:
                        errors.append({"code": field, "message": str(messages), "field": field})
        elif isinstance(detail, list):
            for msg in detail:
                errors.append({"code": "error", "message": str(msg), "field": None})
        else:
            errors.append({"code": "error", "message": str(detail), "field": None})

        response.data = {"errors": errors}

    return response


class ServiceError(Exception):
    """Domain-level error raised by service functions; carries a stable ``code``
    and a user-safe ``message`` that views translate into an error response."""

    def __init__(self, message: str, code: str = "service_error") -> None:
        self.message = message
        self.code = code
        super().__init__(message)
