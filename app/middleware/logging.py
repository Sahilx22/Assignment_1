"""
Middleware that logs every request/response with timing information.
Binds a unique request_id to each log entry for tracing.
"""
import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log method, path, status code, and duration for every HTTP request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        start_time = time.perf_counter()

        # Bind request_id so all downstream log calls include it
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # Attach request_id to response headers for client-side tracing
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        response.headers["X-Request-ID"] = request_id

        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=elapsed_ms,
            client_ip=request.client.host if request.client else "unknown",
        )

        return response
