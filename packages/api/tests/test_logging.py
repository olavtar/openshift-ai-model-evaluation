# This project was developed with assistance from AI tools.
"""Tests for structured JSON logging and correlation ID middleware."""

import json
import logging

from src.core.logging import JSONFormatter


def test_json_formatter_produces_valid_json():
    """Log records should serialize to valid JSON with required fields."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Hello world",
        args=None,
        exc_info=None,
    )
    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["level"] == "INFO"
    assert parsed["message"] == "Hello world"
    assert "timestamp" in parsed
    assert parsed["component"] == "api"


def test_json_formatter_includes_extra_fields():
    """Extra fields like request_id and endpoint should appear in JSON output."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Request handled",
        args=None,
        exc_info=None,
    )
    record.request_id = "abc-123"  # type: ignore[attr-defined]
    record.endpoint = "/health/live"  # type: ignore[attr-defined]
    record.status_code = 200  # type: ignore[attr-defined]

    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["request_id"] == "abc-123"
    assert parsed["endpoint"] == "/health/live"
    assert parsed["status_code"] == 200


def test_json_formatter_includes_exception_info():
    """When exc_info is present, error_type and stack_trace should be included."""
    import sys

    formatter = JSONFormatter()
    try:
        raise ValueError("test error")
    except ValueError:
        exc_info = sys.exc_info()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Something failed",
            args=None,
            exc_info=exc_info,
        )

    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["error_type"] == "ValueError"
    assert "test error" in parsed["error_details"]
    assert "stack_trace" in parsed


def test_json_formatter_omits_absent_optional_fields():
    """Optional fields (request_id, user_id) should not appear when absent."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="No extras",
        args=None,
        exc_info=None,
    )
    output = formatter.format(record)
    parsed = json.loads(output)

    assert "request_id" not in parsed
    assert "user_id" not in parsed


def test_correlation_id_middleware_sets_header(client):
    """Responses should include X-Request-ID header."""
    response = client.get("/health/live")
    assert "x-request-id" in response.headers
    # Should be a valid UUID-like string
    assert len(response.headers["x-request-id"]) > 0


def test_correlation_id_middleware_propagates_incoming_id(client):
    """When the request includes X-Request-ID, the same value should be returned."""
    response = client.get("/health/live", headers={"X-Request-ID": "my-trace-id"})
    assert response.headers["x-request-id"] == "my-trace-id"
