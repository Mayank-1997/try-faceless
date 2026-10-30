"""Correlation ID middleware — injects request-scoped IDs into every log entry.

Adds an ``X-Correlation-ID`` header to requests and responses.  If the
client provides one, it is reused; otherwise a new UUID is generated.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.correlation import generate_correlation_id, set_correlation_id, clear_context


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that manages correlation IDs for request tracing.

    - Reads ``X-Correlation-ID`` from the request header.
    - Generates a new UUID if not provided.
    - Sets the correlation ID in the context for structured logging.
    - Adds the correlation ID to the response header.
    - Clears the context after the request completes.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID") or generate_correlation_id()
        set_correlation_id(correlation_id)

        try:
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = correlation_id
            return response
        finally:
            clear_context()
