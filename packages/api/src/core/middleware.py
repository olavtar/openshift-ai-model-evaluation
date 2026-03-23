# This project was developed with assistance from AI tools.
"""Request middleware for correlation IDs and request logging."""

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Inject or propagate a correlation ID on every request.

    If the incoming request includes an ``X-Request-ID`` header the value is
    reused; otherwise a new UUID4 is generated.  The ID is stored on
    ``request.state.request_id`` and returned in the response header.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log request start and completion with duration and status code."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = getattr(request.state, "request_id", None)
        user_id = request.headers.get("X-Forwarded-User")

        extra = {
            "request_id": request_id,
            "user_id": user_id,
            "endpoint": request.url.path,
            "method": request.method,
        }

        logger.info("Request received", extra=extra)

        start = time.monotonic()
        response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000)

        extra["status_code"] = response.status_code
        extra["duration_ms"] = duration_ms
        logger.info("Request completed", extra=extra)

        return response
