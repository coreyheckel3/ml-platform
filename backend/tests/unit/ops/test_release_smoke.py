from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import pytest
from scripts.ops.release_smoke import (
    HttpSmokeTransport,
    SmokeHttpResponse,
    run_release_smoke,
)

PROJECT_ID = "00000000-0000-4000-8000-000000000001"
TRAINING_RUN_ID = "00000000-0000-4000-8000-000000000002"


class FakeTransport:
    def __init__(self, routes: Mapping[tuple[str, str], SmokeHttpResponse]) -> None:
        self.routes = dict(routes)
        self.calls: list[tuple[str, str, str | None, Mapping[str, Any] | None]] = []

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: Mapping[str, Any] | None = None,
        access_token: str | None = None,
    ) -> SmokeHttpResponse:
        self.calls.append((method, path, access_token, payload))
        return self.routes[(method, path)]


def test_release_smoke_success_calls_control_plane_surfaces() -> None:
    transport = FakeTransport(success_routes())
    expected_auth = success_routes()[("POST", "/api/v1/auth/login")].payload["access_token"]

    report = run_release_smoke(
        base_url="http://127.0.0.1:8001",
        email="admin@forgeml.dev",
        password="forgeml-local-admin",
        transport=transport,
    )

    called_paths = [path for _method, path, _token, _payload in transport.calls]

    assert report["status"] == "passed"
    assert report["selected_project_id"] == PROJECT_ID
    assert "/api/v1/projects" in called_paths
    assert f"/api/v1/projects/{PROJECT_ID}/datasets" in called_paths
    assert f"/api/v1/projects/{PROJECT_ID}/training-runs" in called_paths
    assert f"/api/v1/training-runs/{TRAINING_RUN_ID}/logs" in called_paths
    assert f"/api/v1/projects/{PROJECT_ID}/monitoring/summary" in called_paths
    assert all(
        token == expected_auth
        for method, path, token, _payload in transport.calls
        if path.startswith("/api/v1/") and path != "/api/v1/auth/login"
    )


def test_release_smoke_fails_without_project_context() -> None:
    routes = success_routes()
    routes[("GET", "/api/v1/projects")] = SmokeHttpResponse(200, {"items": []})
    transport = FakeTransport(routes)

    report = run_release_smoke(
        base_url="http://127.0.0.1:8001",
        email="admin@forgeml.dev",
        password="forgeml-local-admin",
        transport=transport,
    )

    called_paths = [path for _method, path, _token, _payload in transport.calls]
    failed_stages = [check["stage"] for check in report["checks"] if check["status"] == "failed"]

    assert report["status"] == "failed"
    assert "project_inventory_context" in failed_stages
    assert f"/api/v1/projects/{PROJECT_ID}/datasets" not in called_paths


def test_release_smoke_stops_after_auth_failure() -> None:
    transport = FakeTransport(
        {
            ("GET", "/health/ready"): SmokeHttpResponse(200, {"status": "ready"}),
            ("POST", "/api/v1/auth/login"): SmokeHttpResponse(
                401,
                {"detail": "Invalid credentials."},
            ),
        }
    )

    report = run_release_smoke(
        base_url="http://127.0.0.1:8001",
        email="admin@forgeml.dev",
        password="wrong",
        transport=transport,
    )

    called_paths = [path for _method, path, _token, _payload in transport.calls]

    assert report["status"] == "failed"
    assert "/api/v1/auth/me" not in called_paths


def test_release_smoke_skips_training_logs_when_no_runs_exist() -> None:
    routes = success_routes()
    routes[("GET", f"/api/v1/projects/{PROJECT_ID}/training-runs")] = SmokeHttpResponse(
        200,
        {"items": []},
    )
    transport = FakeTransport(routes)

    report = run_release_smoke(
        base_url="http://127.0.0.1:8001",
        email="admin@forgeml.dev",
        password="forgeml-local-admin",
        transport=transport,
    )

    log_checks = [
        check for check in report["checks"] if check["stage"] == "training_logs_surface"
    ]

    assert report["status"] == "passed"
    assert log_checks[0]["status"] == "skipped"


def test_release_smoke_skips_optional_training_logs_when_not_found() -> None:
    routes = success_routes()
    routes[("GET", f"/api/v1/training-runs/{TRAINING_RUN_ID}/logs")] = SmokeHttpResponse(
        404,
        {"detail": "Not Found"},
    )
    transport = FakeTransport(routes)

    report = run_release_smoke(
        base_url="http://127.0.0.1:8001",
        email="admin@forgeml.dev",
        password="forgeml-local-admin",
        transport=transport,
    )

    log_checks = [
        check for check in report["checks"] if check["stage"] == "training_logs_surface"
    ]

    assert report["status"] == "passed"
    assert log_checks[0]["status"] == "skipped"
    assert "optional stage unavailable" in log_checks[0]["detail"]


def test_release_smoke_report_is_serializable() -> None:
    report = run_release_smoke(
        base_url="http://127.0.0.1:8001",
        email="admin@forgeml.dev",
        password="forgeml-local-admin",
        transport=FakeTransport(success_routes()),
    )

    assert json.loads(json.dumps(report))["schema_version"] == "forgeml.release_smoke_result.v1"


def test_http_smoke_transport_rejects_invalid_base_url() -> None:
    with pytest.raises(ValueError, match="http or https"):
        HttpSmokeTransport("ftp://127.0.0.1:8001")


def success_routes() -> dict[tuple[str, str], SmokeHttpResponse]:
    project_items = {"items": [{"id": PROJECT_ID, "name": "Fraud Detection"}]}
    empty_items = {"items": []}
    return {
        ("GET", "/health/ready"): SmokeHttpResponse(200, {"status": "ready"}),
        ("POST", "/api/v1/auth/login"): SmokeHttpResponse(200, {"access_token": "access-token"}),
        ("GET", "/api/v1/auth/me"): SmokeHttpResponse(200, {"email": "admin@forgeml.dev"}),
        ("GET", "/api/v1/projects"): SmokeHttpResponse(200, project_items),
        ("GET", f"/api/v1/projects/{PROJECT_ID}/datasets"): SmokeHttpResponse(200, empty_items),
        ("GET", f"/api/v1/projects/{PROJECT_ID}/feature-sets"): SmokeHttpResponse(
            200,
            empty_items,
        ),
        ("GET", f"/api/v1/projects/{PROJECT_ID}/experiments"): SmokeHttpResponse(
            200,
            empty_items,
        ),
        ("GET", f"/api/v1/projects/{PROJECT_ID}/training-runs"): SmokeHttpResponse(
            200,
            {"items": [{"id": TRAINING_RUN_ID}]},
        ),
        ("GET", f"/api/v1/training-runs/{TRAINING_RUN_ID}/logs"): SmokeHttpResponse(
            200,
            {"items": [{"message": "training completed"}]},
        ),
        ("GET", f"/api/v1/projects/{PROJECT_ID}/models"): SmokeHttpResponse(200, empty_items),
        ("GET", f"/api/v1/projects/{PROJECT_ID}/deployments"): SmokeHttpResponse(
            200,
            empty_items,
        ),
        ("GET", f"/api/v1/projects/{PROJECT_ID}/inference-endpoints"): SmokeHttpResponse(
            200,
            empty_items,
        ),
        ("GET", f"/api/v1/projects/{PROJECT_ID}/monitoring/summary"): SmokeHttpResponse(
            200,
            {"project_id": PROJECT_ID, "prediction_count": 0},
        ),
        ("GET", f"/api/v1/projects/{PROJECT_ID}/alert-rules"): SmokeHttpResponse(
            200,
            empty_items,
        ),
        ("GET", f"/api/v1/projects/{PROJECT_ID}/alert-events"): SmokeHttpResponse(
            200,
            empty_items,
        ),
        ("GET", f"/api/v1/projects/{PROJECT_ID}/drift-reports"): SmokeHttpResponse(
            200,
            empty_items,
        ),
        ("GET", f"/api/v1/projects/{PROJECT_ID}/retraining-policies"): SmokeHttpResponse(
            200,
            empty_items,
        ),
        ("GET", f"/api/v1/projects/{PROJECT_ID}/retraining-runs"): SmokeHttpResponse(
            200,
            empty_items,
        ),
    }
