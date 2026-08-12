from fastapi.testclient import TestClient

from forgeml.main import create_app
from forgeml.platform.config import Settings


def test_rate_limiter_partitions_by_client_and_path() -> None:
    settings = Settings(
        rate_limit_requests=1,
        rate_limit_window_seconds=60,
        rate_limit_exempt_paths=[],
    )
    client = TestClient(create_app(settings))

    first = client.get("/health/live", headers={"x-forwarded-for": "203.0.113.10"})
    same_client_same_path = client.get(
        "/health/live",
        headers={"x-forwarded-for": "203.0.113.10"},
    )
    same_client_other_path = client.get(
        "/health/ready",
        headers={"x-forwarded-for": "203.0.113.10"},
    )
    other_client_same_path = client.get(
        "/health/live",
        headers={"x-forwarded-for": "203.0.113.11"},
    )

    assert first.status_code == 200
    assert same_client_same_path.status_code == 429
    assert same_client_same_path.headers["retry-after"] == "60"
    assert same_client_other_path.status_code == 200
    assert other_client_same_path.status_code == 200
