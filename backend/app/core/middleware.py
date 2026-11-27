"""Request ID middleware and context management."""

import uuid
from contextvars import ContextVar
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Context variable to store request ID across async calls
REQUEST_ID_VAR: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    """Get current request ID from context."""
    return REQUEST_ID_VAR.get()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware that assigns a unique request ID to each incoming request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get request ID from header or generate a new one
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = f"req-{uuid.uuid4().hex[:12]}"

        # Set in context var
        token = REQUEST_ID_VAR.set(request_id)

        # Attach to request state for easy access
        request.state.request_id = request_id

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            REQUEST_ID_VAR.reset(token)