from collections.abc import Awaitable, Callable
from time import perf_counter
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from forgeml.platform.observability.metrics import (
    api_request_duration_seconds,
    api_requests_total,
)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        trace_id = request.headers.get("x-request-id", str(uuid4()))
        request.state.trace_id = trace_id
        started_at = perf_counter()
        response = await call_next(request)
        route = getattr(request.scope.get("route"), "path", request.url.path)
        api_requests_total.labels(
            route=route,
            method=request.method,
            status_code=str(response.status_code),
        ).inc()
        api_request_duration_seconds.labels(
            route=route,
            method=request.method,
        ).observe(perf_counter() - started_at)
        response.headers["x-request-id"] = trace_id
        return response
