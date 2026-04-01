from __future__ import annotations

import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.log_context import set_request_id


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        request_id = (
            request.headers.get("x-request-id") or f"req_{uuid.uuid4().hex[:12]}"
        )
        set_request_id(request_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            # Best-effort reset for next request on same worker context.
            set_request_id(None)

        duration_ms = (time.perf_counter() - start) * 1000.0
        response.headers["x-request-id"] = request_id
        # Store for any downstream tools/clients; not used in logging directly.
        response.headers["x-response-time-ms"] = f"{duration_ms:.1f}"
        return response
