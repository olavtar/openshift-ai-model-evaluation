# This project was developed with assistance from AI tools.
"""Consistent error handling framework.

Defines the error response schema, error code catalog, and FastAPI exception
handlers that ensure every API error follows a uniform JSON shape.
"""

import enum
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ErrorCode(str, enum.Enum):
    """Catalog of machine-readable error codes."""

    UNAUTHORIZED = "UNAUTHORIZED"
    CONTENT_POLICY_VIOLATION = "CONTENT_POLICY_VIOLATION"
    INVALID_INPUT = "INVALID_INPUT"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    DATABASE_UNAVAILABLE = "DATABASE_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    NOT_FOUND = "NOT_FOUND"


# Default HTTP status codes per error code
_STATUS_MAP: dict[ErrorCode, int] = {
    ErrorCode.UNAUTHORIZED: 401,
    ErrorCode.CONTENT_POLICY_VIOLATION: 400,
    ErrorCode.INVALID_INPUT: 400,
    ErrorCode.FILE_TOO_LARGE: 413,
    ErrorCode.RATE_LIMIT_EXCEEDED: 429,
    ErrorCode.MODEL_UNAVAILABLE: 503,
    ErrorCode.DATABASE_UNAVAILABLE: 500,
    ErrorCode.INTERNAL_ERROR: 500,
    ErrorCode.NOT_FOUND: 404,
}


class ErrorDetail(BaseModel):
    """Inner error detail returned inside the ``error`` envelope."""

    code: str
    message: str
    details: str | None = None


class ErrorResponse(BaseModel):
    """Top-level error response envelope per REQ-5-008."""

    error: ErrorDetail


class AppError(Exception):
    """Application-level error that maps to a structured JSON response."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: str | None = None,
        status_code: int | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details
        self.status_code = status_code or _STATUS_MAP.get(code, 500)
        super().__init__(message)


def _build_error_response(
    code: str, message: str, details: str | None, status_code: int
) -> JSONResponse:
    body = ErrorResponse(error=ErrorDetail(code=code, message=message, details=details))
    return JSONResponse(status_code=status_code, content=body.model_dump())


def _get_request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach global exception handlers to the FastAPI application."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        request_id = _get_request_id(request)
        logger.warning(
            "Application error: %s",
            exc.message,
            extra={"request_id": request_id, "error_type": exc.code.value},
        )
        return _build_error_response(
            code=exc.code.value,
            message=exc.message,
            details=exc.details,
            status_code=exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        first_error = exc.errors()[0] if exc.errors() else {}
        field = " -> ".join(str(loc) for loc in first_error.get("loc", []))
        msg = first_error.get("msg", "Validation error")
        return _build_error_response(
            code=ErrorCode.INVALID_INPUT.value,
            message=f"Invalid input: {msg}",
            details=f"Field: {field}" if field else None,
            status_code=400,
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = _get_request_id(request)
        logger.error(
            "Unhandled exception",
            exc_info=exc,
            extra={"request_id": request_id},
        )
        return _build_error_response(
            code=ErrorCode.INTERNAL_ERROR.value,
            message=(
                "An unexpected error occurred. Please try again or contact support."
            ),
            details=f"Request ID: {request_id}" if request_id else None,
            status_code=500,
        )
