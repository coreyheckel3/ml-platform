from fastapi.testclient import TestClient

from forgeml.main import create_app
from forgeml.platform.config import Settings


def test_health_endpoints_return_service_status() -> None:
    client = TestClient(create_app())

    live = client.get("/health/live")
    ready = client.get("/health/ready")

    assert live.status_code == 200
    assert ready.status_code == 200
    assert live.json()["status"] == "live"
    assert ready.json()["status"] == "ready"


def test_metrics_endpoint_exposes_http_request_metrics() -> None:
    client = TestClient(create_app())

    client.get("/health/live")
    metrics = client.get("/metrics")

    assert metrics.status_code == 200
    assert "forgeml_api_requests_total" in metrics.text
    assert 'route="/health/live"' in metrics.text


def test_security_headers_are_applied_to_api_responses() -> None:
    client = TestClient(create_app())

    response = client.get("/health/live")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"
    assert response.headers["cross-origin-opener-policy"] == "same-origin"


def test_rate_limiter_rejects_excess_requests() -> None:
    settings = Settings(
        rate_limit_requests=2,
        rate_limit_window_seconds=60,
        rate_limit_exempt_paths=[],
    )
    client = TestClient(create_app(settings))

    first = client.get("/health/live")
    second = client.get("/health/live")
    third = client.get("/health/live")

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.json() == {"detail": "Rate limit exceeded."}
    assert third.headers["x-ratelimit-limit"] == "2"
    assert third.headers["x-ratelimit-remaining"] == "0"
    assert third.headers["retry-after"] == "60"
    assert third.headers["x-request-id"]
    assert third.headers["x-content-type-options"] == "nosniff"
