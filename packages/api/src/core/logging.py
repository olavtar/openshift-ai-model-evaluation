# This project was developed with assistance from AI tools.
"""Structured JSON logging configuration.

Configures Python logging to emit JSON-formatted log entries to stdout with
consistent fields: timestamp, level, component, request_id, message.
"""

import json
import logging
import sys
from datetime import UTC, datetime


class JSONFormatter(logging.Formatter):
    """Format log records as JSON with required structured fields."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "component": getattr(record, "component", "api"),
            "message": record.getMessage(),
        }

        request_id = getattr(record, "request_id", None)
        if request_id:
            log_entry["request_id"] = request_id

        user_id = getattr(record, "user_id", None)
        if user_id:
            log_entry["user_id"] = user_id

        if record.exc_info and not isinstance(record.exc_info, bool) and record.exc_info[1] is not None:
            log_entry["error_type"] = type(record.exc_info[1]).__name__
            log_entry["error_details"] = str(record.exc_info[1])
            log_entry["stack_trace"] = self.formatException(record.exc_info)

        for key in ("endpoint", "method", "status_code", "duration_ms", "model"):
            value = getattr(record, key, None)
            if value is not None:
                log_entry[key] = value

        return json.dumps(log_entry, default=str)


def setup_logging(level: str = "INFO") -> None:
    """Configure root logger with JSON formatter on stdout."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicate output
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root.addHandler(handler)

    # Quiet noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
