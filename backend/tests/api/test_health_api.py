from fastapi.testclient import TestClient

from forgeml.main import create_app
from forgeml.platform.config import Settings
from forgeml.platform.health import DependencyProbe, ReadinessChecker


def test_health_endpoints_return_service_status() -> None:
    client = TestClient(create_app())

    live = client.get("/health/live")
    ready = client.get("/health/ready")

    assert live.status_code == 200
    assert ready.status_code == 200
    assert live.json()["status"] == "live"
    assert ready.json()["status"] == "ready"
    assert ready.json()["checks_enabled"] is False
    assert ready.json()["checks"] == []


def test_ready_endpoint_returns_probe_results_when_dependency_checks_pass() -> None:
    checker = ReadinessChecker(
        service_name="forgeml-api",
        checks_enabled=True,
        probes=[
            DependencyProbe(name="database", check=lambda: None),
            DependencyProbe(name="redis", check=lambda: None),
        ],
    )
    client = TestClient(create_app(readiness_checker=checker))

    response = client.get("/health/ready")
    payload = response.json()

    assert response.status_code == 200
    assert payload["status"] == "ready"
    assert payload["checks_enabled"] is True
    assert [(check["name"], check["status"]) for check in payload["checks"]] == [
        ("database", "pass"),
        ("redis", "pass"),
    ]


def test_ready_endpoint_returns_503_when_dependency_check_fails() -> None:
    def fail_database() -> None:
        raise RuntimeError("postgresql://user:password@internal")

    checker = ReadinessChecker(
        service_name="forgeml-api",
        checks_enabled=True,
        probes=[DependencyProbe(name="database", check=fail_database)],
    )
    client = TestClient(create_app(readiness_checker=checker))

    response = client.get("/health/ready")
    payload = response.json()

    assert response.status_code == 503
    assert payload["status"] == "not_ready"
    assert payload["checks"][0]["name"] == "database"
    assert payload["checks"][0]["status"] == "fail"
    assert payload["checks"][0]["message"] == "Probe raised RuntimeError."
    assert "password" not in response.text


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
