from fastapi.testclient import TestClient

from forgeml.main import create_app


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
