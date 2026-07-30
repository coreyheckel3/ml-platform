import json
from pathlib import Path

from scripts.ci.production_readiness import run_checks


def test_production_readiness_checks_pass() -> None:
    checks = run_checks(Path("."))

    failed = [check for check in checks if not check.passed]

    assert failed == []


def test_grafana_dashboard_has_prometheus_panels() -> None:
    dashboard = json.loads(
        Path("infra/observability/grafana/dashboards/forgeml-platform.json").read_text(
            encoding="utf-8"
        )
    )

    panel_titles = {panel["title"] for panel in dashboard["panels"]}

    assert dashboard["uid"] == "forgeml-platform-health"
    assert {
        "API Request Rate",
        "API Latency P95",
        "API Error Rate",
        "Rate Limited Requests",
    }.issubset(panel_titles)


def test_compose_file_mounts_observability_configuration() -> None:
    compose = Path("infra/compose/docker-compose.yml").read_text(encoding="utf-8")

    assert "../observability/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro" in compose
    assert "../observability/grafana/provisioning:/etc/grafana/provisioning:ro" in compose
    assert "../observability/grafana/dashboards:/var/lib/grafana/dashboards:ro" in compose
    assert "grafana-data:" in compose


def test_frontend_supply_chain_gate_is_enforced() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    package_lock = json.loads(Path("frontend/package-lock.json").read_text(encoding="utf-8"))
    packages = package_lock["packages"]

    assert "npm --prefix frontend audit --omit=dev" in workflow
    assert "node_modules/react-router" not in packages
    assert "node_modules/react-router-dom" not in packages


def test_frontend_performance_gate_is_enforced() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    app_source = Path("frontend/src/app/App.tsx").read_text(encoding="utf-8")
    routes_source = Path("frontend/src/app/routes.tsx").read_text(encoding="utf-8")

    assert "python scripts/ci/check_frontend_bundle_budget.py" in workflow
    assert "<Suspense fallback={<RouteLoadingState />}" in app_source
    assert routes_source.count("lazy(() =>") >= 10


def test_openapi_contract_gate_is_enforced() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    contract = json.loads(
        Path("contracts/openapi/forgeml.v1.openapi.json").read_text(encoding="utf-8")
    )
    paths = contract["paths"]

    assert "python scripts/ci/generate_openapi_contract.py --check" in workflow
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/projects/{project_id}/training-runs" in paths
    assert "/api/v1/inference-endpoints/{endpoint_id}/predict" in paths
