import json
import logging
import threading

_request_id_local = threading.local()

# Standard attributes every LogRecord carries (levelno, pathname, exc_info, …).
# Anything outside this set was passed via `extra=` and is what we want to emit;
# this also stops non-serialisable internals (e.g. the exc_info tuple) from
# leaking into the JSON payload.
_RESERVED_RECORD_KEYS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {
    "message",
    "asctime",
}


def set_request_id(request_id: str) -> None:
    """Bind the current request's ID to thread-local storage for log correlation."""
    _request_id_local.request_id = request_id


def get_request_id() -> str:
    """Return the current thread's request ID, or ``"-"`` when none is set."""
    return getattr(_request_id_local, "request_id", "-")


class JSONFormatter(logging.Formatter):
    """Log formatter that emits one JSON object per record, injects the request
    ID, and drops sensitive `extra` keys (passwords, tokens, embeddings, …)."""

    SENSITIVE_KEYS = {"password", "token", "api_key", "secret", "embedding", "content"}

    def format(self, record: logging.LogRecord) -> str:
        """Serialise the log record to a JSON string with request-id and safe extras."""
        log_entry = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": get_request_id(),
        }

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        extra = {
            k: v
            for k, v in record.__dict__.items()
            if k not in _RESERVED_RECORD_KEYS and k.lower() not in self.SENSITIVE_KEYS
        }
        if extra:
            log_entry["extra"] = extra

        return json.dumps(log_entry)
