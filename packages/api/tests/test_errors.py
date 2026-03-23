# This project was developed with assistance from AI tools.
"""Tests for the error handling framework."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.core.errors import AppError, ErrorCode, register_exception_handlers


def _make_app() -> FastAPI:
    """Create a minimal app with error handlers for isolated testing."""
    app = FastAPI()
    register_exception_handlers(app)
    return app


def test_app_error_returns_structured_response():
    """AppError should produce the standard {error: {code, message, details}} shape."""
    app = _make_app()

    @app.get("/fail")
    async def fail():
        raise AppError(
            code=ErrorCode.MODEL_UNAVAILABLE,
            message="Model A is currently unavailable.",
            details="Connection refused",
        )

    client = TestClient(app)
    response = client.get("/fail")

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "MODEL_UNAVAILABLE"
    assert body["error"]["message"] == "Model A is currently unavailable."
    assert body["error"]["details"] == "Connection refused"


def test_app_error_custom_status_code():
    """AppError should allow overriding the default HTTP status for its code."""
    app = _make_app()

    @app.get("/custom")
    async def custom():
        raise AppError(
            code=ErrorCode.INVALID_INPUT,
            message="Bad input",
            status_code=422,
        )

    client = TestClient(app)
    response = client.get("/custom")
    assert response.status_code == 422


def test_validation_error_returns_structured_response():
    """Pydantic validation errors should be caught and formatted consistently."""
    from pydantic import BaseModel

    app = _make_app()

    class Payload(BaseModel):
        name: str

    @app.post("/validate")
    async def validate(payload: Payload):
        return {"ok": True}

    client = TestClient(app)
    response = client.post("/validate", json={})

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "INVALID_INPUT"
    assert "name" in (body["error"].get("details") or "")


def test_unhandled_exception_returns_500():
    """Unhandled exceptions should produce a safe 500 with INTERNAL_ERROR code."""
    app = _make_app()

    @app.get("/boom")
    async def boom():
        raise RuntimeError("unexpected failure")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/boom")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_ERROR"
    # Must NOT leak the exception message to the client
    assert "unexpected failure" not in body["error"]["message"]


def test_error_code_catalog_completeness():
    """Every ErrorCode should have a default HTTP status mapping."""
    from src.core.errors import _STATUS_MAP

    for code in ErrorCode:
        assert code in _STATUS_MAP, f"ErrorCode.{code.name} missing from _STATUS_MAP"
