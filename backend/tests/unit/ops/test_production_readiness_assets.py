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


def test_problem_details_contract_gate_is_enforced() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    contract = json.loads(Path("contracts/api/problem-details.v1.json").read_text(encoding="utf-8"))
    handlers_source = Path("backend/src/forgeml/platform/api/errors.py").read_text(
        encoding="utf-8"
    )
    problem_source = Path("backend/src/forgeml/platform/api/problem_details.py").read_text(
        encoding="utf-8"
    )
    domain_error_codes = {error["code"] for error in contract["domain_errors"]}

    assert "python scripts/ci/check_problem_details_contract.py" in workflow
    assert "trace_id" in contract["required_fields"]
    assert "input" not in contract["validation_error_required_fields"]
    assert {"validation_failed", "resource_not_found", "internal_error"}.issubset(
        domain_error_codes
    )
    assert "RequestValidationError" in handlers_source
    assert "StarletteHTTPException" in handlers_source
    assert "INTERNAL_ERROR_DETAIL" in problem_source


def test_api_authorization_contract_gate_is_enforced() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    contract = json.loads(
        Path("contracts/security/api-authorization.v1.json").read_text(encoding="utf-8")
    )
    public_routes = {(route["method"], route["path"]) for route in contract["public_routes"]}
    protected_routes = {(route["method"], route["path"]) for route in contract["protected_routes"]}

    assert "python scripts/ci/check_api_authorization_contract.py" in workflow
    assert ("POST", "/api/v1/auth/login") in public_routes
    assert ("GET", "/api/v1/auth/me") in protected_routes
    assert ("POST", "/api/v1/inference-endpoints/{endpoint_id}/predict") in protected_routes


def test_permission_catalog_gate_is_enforced() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    contract = json.loads(
        Path("contracts/security/permission-catalog.v1.json").read_text(encoding="utf-8")
    )
    permissions = {permission["code"] for permission in contract["permissions"]}
    roles = {role["code"] for role in contract["role_presets"]}

    assert "python scripts/ci/check_permission_catalog.py" in workflow
    assert "training_runs:create" in permissions
    assert "inference:predict" in permissions
    assert "model_versions:review" in permissions
    assert {"platform_admin", "ml_engineer", "ml_operator", "ml_viewer"}.issubset(roles)


def test_runtime_config_policy_gate_is_enforced() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    contract = json.loads(
        Path("contracts/security/runtime-config-policy.v1.json").read_text(encoding="utf-8")
    )
    guardrails = {guardrail["code"] for guardrail in contract["guardrails"]}

    assert "python scripts/ci/check_runtime_config_policy.py" in workflow
    assert "production" in contract["production_like_environments"]
    assert "staging" in contract["production_like_environments"]
    assert "jwt_secret_not_default" in guardrails
    assert "docs_disabled" in guardrails
    assert "cors_no_wildcard" in guardrails
    assert "readiness_checks_enabled" in guardrails
    assert "database_url_not_localhost" in guardrails


def test_readiness_probe_contract_is_enforced() -> None:
    config_source = Path("backend/src/forgeml/platform/config.py").read_text(encoding="utf-8")
    health_source = Path("backend/src/forgeml/platform/health.py").read_text(encoding="utf-8")
    metrics_source = Path("backend/src/forgeml/platform/observability/metrics.py").read_text(
        encoding="utf-8"
    )
    contract = json.loads(
        Path("contracts/openapi/forgeml.v1.openapi.json").read_text(encoding="utf-8")
    )
    ready_responses = contract["paths"]["/health/ready"]["get"]["responses"]

    assert "FORGEML_READINESS_CHECKS_ENABLED" in config_source
    assert "ReadinessChecker" in health_source
    assert "check_database_connection" in health_source
    assert "check_redis_connection" in health_source
    assert "forgeml_readiness_probe_status" in metrics_source
    assert "forgeml_readiness_probe_duration_seconds" in metrics_source
    assert "503" in ready_responses


def test_request_logging_contract_gate_is_enforced() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    contract = json.loads(
        Path("contracts/observability/request-log-event.v1.json").read_text(encoding="utf-8")
    )
    logging_source = Path("backend/src/forgeml/platform/observability/logging.py").read_text(
        encoding="utf-8"
    )
    middleware_source = Path("backend/src/forgeml/platform/api/middleware.py").read_text(
        encoding="utf-8"
    )

    assert "python scripts/ci/check_request_logging_contract.py" in workflow
    assert "trace_id" in contract["required_top_level_fields"]
    assert "duration_ms" in contract["required_http_fields"]
    assert "token" in contract["redaction"]["sensitive_field_markers"]
    assert "JsonLogFormatter" in logging_source
    assert "redact_mapping" in logging_source
    assert "log_http_request" in middleware_source
