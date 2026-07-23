from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from math import ceil
from time import monotonic, perf_counter
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from forgeml.platform.observability.metrics import (
    api_request_duration_seconds,
    api_requests_total,
    rate_limited_requests_total,
)

SECURITY_HEADERS = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "no-referrer",
    "permissions-policy": "camera=(), microphone=(), geolocation=()",
    "cross-origin-opener-policy": "same-origin",
}


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


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, environment: str) -> None:
        super().__init__(app)
        self._environment = environment

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        for header, value in SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        if self._environment != "local":
            response.headers.setdefault(
                "strict-transport-security",
                "max-age=31536000; includeSubDomains",
            )
        return response


@dataclass
class _Window:
    opened_at: float
    count: int


class FixedWindowRateLimiter:
    def __init__(self, limit: int, window_seconds: int) -> None:
        self._limit = limit
        self._window_seconds = window_seconds
        self._windows: dict[str, _Window] = {}

    def check(self, key: str, now: float | None = None) -> tuple[bool, int, int]:
        current_time = monotonic() if now is None else now
        window = self._windows.get(key)
        if window is None or current_time - window.opened_at >= self._window_seconds:
            self._windows[key] = _Window(opened_at=current_time, count=1)
            return True, self._limit - 1, self._window_seconds

        reset_seconds = max(ceil(self._window_seconds - (current_time - window.opened_at)), 1)
        if window.count >= self._limit:
            return False, 0, reset_seconds

        window.count += 1
        return True, self._limit - window.count, reset_seconds


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        enabled: bool,
        requests_per_window: int,
        window_seconds: int,
        exempt_paths: list[str],
    ) -> None:
        super().__init__(app)
        self._enabled = enabled
        self._requests_per_window = requests_per_window
        self._limiter = FixedWindowRateLimiter(requests_per_window, window_seconds)
        self._exempt_paths = tuple(exempt_paths)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if not self._enabled or self._is_exempt(request.url.path):
            return await call_next(request)

        key = self._client_key(request)
        allowed, remaining, reset_seconds = self._limiter.check(key)
        headers = {
            "x-ratelimit-limit": str(self._requests_per_window),
            "x-ratelimit-remaining": str(remaining),
            "x-ratelimit-reset": str(reset_seconds),
        }
        if not allowed:
            route = getattr(request.scope.get("route"), "path", request.url.path)
            rate_limited_requests_total.labels(route=route, method=request.method).inc()
            headers["retry-after"] = str(reset_seconds)
            return JSONResponse(
                {"detail": "Rate limit exceeded."},
                status_code=429,
                headers=headers,
            )

        response = await call_next(request)
        for header, value in headers.items():
            response.headers.setdefault(header, value)
        return response

    def _is_exempt(self, path: str) -> bool:
        return any(path == exempt or path.startswith(f"{exempt}/") for exempt in self._exempt_paths)

    def _client_key(self, request: Request) -> str:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_host = forwarded_for.split(",", maxsplit=1)[0].strip()
        elif request.client:
            client_host = request.client.host
        else:
            client_host = "unknown"
        return f"{client_host}:{request.url.path}"
