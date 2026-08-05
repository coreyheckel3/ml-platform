from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    from scripts.ci.check_alembic_migration_contract import (
        check_migration_contract as verify_alembic_migration_contract,
    )
    from scripts.ci.check_sqlalchemy_schema_contract import (
        check_schema_contract as verify_sqlalchemy_schema_contract,
    )
except ModuleNotFoundError:
    from check_alembic_migration_contract import (  # type: ignore[no-redef]
        check_migration_contract as verify_alembic_migration_contract,
    )
    from check_sqlalchemy_schema_contract import (  # type: ignore[no-redef]
        check_schema_contract as verify_sqlalchemy_schema_contract,
    )

REPO_ROOT = Path(__file__).resolve().parents[2]
BANNED_TOKENS = ("TO" + "DO", "T" + "BD", "FIX" + "ME", "place" + "holder")
SCAN_ROOTS = (
    "backend/src",
    "backend/tests",
    "frontend/src",
    "frontend/tests",
    "infra",
    "load",
    "ml",
    "examples",
    "scripts",
    "docs",
    "README.md",
)
REQUIRED_FILES = (
    ".github/workflows/ci.yml",
    ".github/workflows/terraform-plan.yml",
    "docs/runbooks/backup-restore.md",
    "docs/runbooks/incident-response.md",
    "docs/runbooks/production-readiness.md",
    "docs/security/threat-model.md",
    "infra/compose/docker-compose.yml",
    "infra/observability/prometheus/prometheus.yml",
    "infra/observability/grafana/provisioning/datasources/prometheus.yml",
    "infra/observability/grafana/provisioning/dashboards/dashboards.yml",
    "infra/observability/grafana/dashboards/forgeml-platform.json",
    "infra/terraform/environments/staging/main.tf",
    "infra/terraform/environments/staging/outputs.tf",
    "infra/terraform/environments/staging/variables.tf",
    "infra/terraform/environments/staging/versions.tf",
    "load/k6/api_smoke.js",
    "backend/src/forgeml/modules/training/infrastructure/execution.py",
    "backend/tests/unit/training/test_training_execution.py",
    "backend/src/forgeml/platform/health.py",
    "backend/tests/unit/platform/test_health.py",
    "scripts/workers/run_training_worker.py",
    "ml/examples/fraud_detection/train.py",
    "ml/examples/movie_recommendation/train.py",
    "ml/examples/semantic_search/build_index.py",
    "scripts/examples/run_local_training.py",
    "scripts/ops/backup_postgres.sh",
    "scripts/ops/restore_postgres.sh",
    "backend/tests/unit/ml/test_example_training_pipelines.py",
    "scripts/ci/check_frontend_bundle_budget.py",
    "scripts/ci/check_alembic_migration_contract.py",
    "contracts/database/README.md",
    "contracts/database/alembic-migrations.v1.json",
    "backend/tests/unit/ops/test_alembic_migration_contract.py",
    "scripts/ci/check_sqlalchemy_schema_contract.py",
    "contracts/database/sqlalchemy-schema.v1.json",
    "backend/tests/unit/ops/test_sqlalchemy_schema_contract.py",
    "scripts/ci/generate_openapi_contract.py",
    "contracts/openapi/forgeml.v1.openapi.json",
    "backend/src/forgeml/platform/api/problem_details.py",
    "backend/tests/api/test_problem_details_api.py",
    "backend/tests/unit/platform/test_problem_details.py",
    "scripts/ci/check_problem_details_contract.py",
    "contracts/api/README.md",
    "contracts/api/problem-details.v1.json",
    "scripts/ci/check_api_authorization_contract.py",
    "contracts/security/api-authorization.v1.json",
    "scripts/ci/check_permission_catalog.py",
    "contracts/security/permission-catalog.v1.json",
    "backend/src/forgeml/platform/config_policy.py",
    "scripts/ci/check_runtime_config_policy.py",
    "contracts/security/runtime-config-policy.v1.json",
    "backend/src/forgeml/platform/observability/logging.py",
    "backend/tests/unit/observability/test_logging.py",
    "backend/tests/api/test_request_logging_api.py",
    "scripts/ci/check_request_logging_contract.py",
    "contracts/observability/README.md",
    "contracts/observability/request-log-event.v1.json",
)


@dataclass(frozen=True)
class ReadinessCheck:
    name: str
    passed: bool
    detail: str


def run_checks(repo_root: Path = REPO_ROOT) -> list[ReadinessCheck]:
    return [
        check_required_files(repo_root),
        check_marker_scan(repo_root),
        check_grafana_dashboard(repo_root),
        check_observability_compose_wiring(repo_root),
        check_ops_scripts(repo_root),
        check_load_test_contract(repo_root),
        check_staging_terraform(repo_root),
        check_example_training_contract(repo_root),
        check_training_execution_contract(repo_root),
        check_alembic_migration_contract(repo_root),
        check_sqlalchemy_schema_contract(repo_root),
        check_frontend_supply_chain_contract(repo_root),
        check_frontend_performance_contract(repo_root),
        check_readiness_probe_contract(repo_root),
        check_openapi_contract(repo_root),
        check_problem_details_contract(repo_root),
        check_api_authorization_contract(repo_root),
        check_permission_catalog_contract(repo_root),
        check_runtime_config_policy_contract(repo_root),
        check_request_logging_contract(repo_root),
    ]


def check_required_files(repo_root: Path) -> ReadinessCheck:
    missing = [path for path in REQUIRED_FILES if not (repo_root / path).is_file()]
    return ReadinessCheck(
        name="required production assets",
        passed=not missing,
        detail="all required assets exist" if not missing else f"missing: {', '.join(missing)}",
    )


def check_marker_scan(repo_root: Path) -> ReadinessCheck:
    findings: list[str] = []
    for root in SCAN_ROOTS:
        path = repo_root / root
        if path.is_file():
            _scan_file(path, repo_root, findings)
            continue
        for file_path in path.rglob("*"):
            if file_path.is_file():
                _scan_file(file_path, repo_root, findings)

    return ReadinessCheck(
        name="source hygiene marker scan",
        passed=not findings,
        detail="no banned markers found" if not findings else "; ".join(findings[:10]),
    )


def check_grafana_dashboard(repo_root: Path) -> ReadinessCheck:
    dashboard_path = repo_root / "infra/observability/grafana/dashboards/forgeml-platform.json"
    dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))
    panels = dashboard.get("panels", [])
    titles = {panel.get("title") for panel in panels}
    required_titles = {
        "API Request Rate",
        "API Latency P95",
        "API Error Rate",
        "Rate Limited Requests",
    }
    missing_titles = sorted(required_titles - titles)
    return ReadinessCheck(
        name="grafana dashboard contract",
        passed=not missing_titles and dashboard.get("uid") == "forgeml-platform-health",
        detail=(
            "dashboard has required panels"
            if not missing_titles
            else f"missing panels: {', '.join(missing_titles)}"
        ),
    )


def check_observability_compose_wiring(repo_root: Path) -> ReadinessCheck:
    compose = (repo_root / "infra/compose/docker-compose.yml").read_text(encoding="utf-8")
    required_fragments = (
        "../observability/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro",
        "../observability/grafana/provisioning:/etc/grafana/provisioning:ro",
        "../observability/grafana/dashboards:/var/lib/grafana/dashboards:ro",
        "grafana-data:",
        "postgres-data:",
    )
    missing = [fragment for fragment in required_fragments if fragment not in compose]
    return ReadinessCheck(
        name="compose observability wiring",
        passed=not missing,
        detail="compose mounts observability assets" if not missing else f"missing: {missing}",
    )


def check_ops_scripts(repo_root: Path) -> ReadinessCheck:
    scripts = [
        repo_root / "scripts/ops/backup_postgres.sh",
        repo_root / "scripts/ops/restore_postgres.sh",
    ]
    invalid = [
        script.relative_to(repo_root).as_posix()
        for script in scripts
        if "set -euo pipefail" not in script.read_text(encoding="utf-8")
    ]
    return ReadinessCheck(
        name="ops script safety flags",
        passed=not invalid,
        detail="ops scripts use strict shell mode" if not invalid else f"invalid: {invalid}",
    )


def check_load_test_contract(repo_root: Path) -> ReadinessCheck:
    load_test = (repo_root / "load/k6/api_smoke.js").read_text(encoding="utf-8")
    required_fragments = ("http_req_failed", "http_req_duration", "/health/ready", "/metrics")
    missing = [fragment for fragment in required_fragments if fragment not in load_test]
    return ReadinessCheck(
        name="load test contract",
        passed=not missing,
        detail="load smoke test has thresholds" if not missing else f"missing: {missing}",
    )


def check_staging_terraform(repo_root: Path) -> ReadinessCheck:
    staging_dir = repo_root / "infra/terraform/environments/staging"
    expected = {"main.tf", "outputs.tf", "variables.tf", "versions.tf"}
    found = {path.name for path in staging_dir.iterdir() if path.is_file()}
    missing = sorted(expected - found)
    main_tf = (staging_dir / "main.tf").read_text(encoding="utf-8")
    uses_variables = "var.project_name" in main_tf and "var.availability_zones" in main_tf
    return ReadinessCheck(
        name="staging terraform contract",
        passed=not missing and uses_variables,
        detail=(
            "staging terraform is variable driven"
            if not missing and uses_variables
            else f"missing={missing}, uses_variables={uses_variables}"
        ),
    )


def check_example_training_contract(repo_root: Path) -> ReadinessCheck:
    trainer_paths = [
        "ml/examples/fraud_detection/train.py",
        "ml/examples/movie_recommendation/train.py",
        "ml/examples/semantic_search/build_index.py",
    ]
    paths = [
        *trainer_paths,
        "scripts/examples/run_local_training.py",
    ]
    missing = [path for path in paths if not (repo_root / path).is_file()]
    if missing:
        return ReadinessCheck(
            name="example training contract",
            passed=False,
            detail=f"missing: {', '.join(missing)}",
        )

    trainer_sources = [
        (path, (repo_root / path).read_text(encoding="utf-8")) for path in trainer_paths
    ]
    orchestrator = (repo_root / "scripts/examples/run_local_training.py").read_text(
        encoding="utf-8"
    )
    required_slugs = {"fraud-detection", "movie-recommendation", "semantic-search"}
    missing_slugs = sorted(slug for slug in required_slugs if slug not in orchestrator)
    missing_schema = [
        path
        for path, source in trainer_sources
        if "forgeml.example_model_artifact.v1" not in source
    ]
    has_manifest_output = "training-summary.json" in orchestrator
    has_project_summary_output = all("summary.json" in source for _path, source in trainer_sources)
    passed = (
        not missing_slugs
        and not missing_schema
        and has_manifest_output
        and has_project_summary_output
    )
    return ReadinessCheck(
        name="example training contract",
        passed=passed,
        detail=(
            "example trainers and orchestrator expose versioned artifacts"
            if passed
            else (
                f"missing_slugs={missing_slugs}, "
                f"missing_schema={missing_schema}, "
                f"has_manifest_output={has_manifest_output}, "
                f"has_project_summary_output={has_project_summary_output}"
            )
        ),
    )


def check_training_execution_contract(repo_root: Path) -> ReadinessCheck:
    service_source = (
        repo_root / "backend/src/forgeml/modules/training/application/services.py"
    ).read_text(encoding="utf-8")
    config_source = (repo_root / "backend/src/forgeml/platform/config.py").read_text(
        encoding="utf-8"
    )
    routes_source = (repo_root / "backend/src/forgeml/modules/training/api/routes.py").read_text(
        encoding="utf-8"
    )
    runner_source = (
        repo_root / "backend/src/forgeml/modules/training/infrastructure/execution.py"
    ).read_text(encoding="utf-8")
    bootstrap_source = (repo_root / "scripts/examples/bootstrap_examples.py").read_text(
        encoding="utf-8"
    )
    required_fragments = {
        "execute_training_run": service_source,
        "execute_next_training_runs": service_source,
        "TrainingJobRunner": service_source,
        "forgeml.training_execution_result.v1": service_source,
        "EXAMPLE_PROJECT_SLUG_PARAMETER": runner_source,
        "LocalExampleTrainingRunner": runner_source,
        "FORGEML_LOCAL_TRAINING_ARTIFACT_ROOT": config_source,
        "runner=LocalExampleTrainingRunner": routes_source,
        "build_training_execution_report": bootstrap_source,
        "claim_training_run": (
            repo_root / "backend/src/forgeml/modules/training/repositories/interfaces.py"
        ).read_text(encoding="utf-8"),
        "run_once": (repo_root / "scripts/workers/run_training_worker.py").read_text(
            encoding="utf-8"
        ),
    }
    missing = [
        fragment for fragment, source in required_fragments.items() if fragment not in source
    ]
    return ReadinessCheck(
        name="training execution contract",
        passed=not missing,
        detail=(
            "training execution runner is wired behind application contracts"
            if not missing
            else f"missing: {missing}"
        ),
    )


def check_alembic_migration_contract(repo_root: Path) -> ReadinessCheck:
    ci_source = (repo_root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    contract_path = repo_root / "contracts/database/alembic-migrations.v1.json"
    versions_dir = repo_root / "backend/alembic/versions"
    has_ci_gate = "python scripts/ci/check_alembic_migration_contract.py" in ci_source
    if not contract_path.is_file():
        return ReadinessCheck(
            name="alembic migration contract",
            passed=False,
            detail=f"missing contract: {contract_path}",
        )

    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    summary = contract.get("summary", {})
    migrations = contract.get("migrations", [])
    contract_current, contract_detail = verify_alembic_migration_contract(
        contract_path,
        versions_dir,
        repo_root,
    )
    has_single_base = summary.get("base_count") == 1 and bool(summary.get("base_revision"))
    has_single_head = summary.get("head_count") == 1 and bool(summary.get("head_revision"))
    has_migration_depth = summary.get("migration_count", 0) >= 12
    has_reversible_migrations = all(
        migration.get("has_upgrade") and migration.get("has_downgrade")
        for migration in migrations
    )
    passed = (
        has_ci_gate
        and contract_current
        and has_single_base
        and has_single_head
        and has_migration_depth
        and has_reversible_migrations
    )
    return ReadinessCheck(
        name="alembic migration contract",
        passed=passed,
        detail=(
            "Alembic topology, single head, reversible migrations, and CI gate are configured"
            if passed
            else (
                f"has_ci_gate={has_ci_gate}, "
                f"contract_current={contract_current}, "
                f"contract_detail={contract_detail}, "
                f"has_single_base={has_single_base}, "
                f"has_single_head={has_single_head}, "
                f"has_migration_depth={has_migration_depth}, "
                f"has_reversible_migrations={has_reversible_migrations}"
            )
        ),
    )


def check_sqlalchemy_schema_contract(repo_root: Path) -> ReadinessCheck:
    ci_source = (repo_root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    contract_path = repo_root / "contracts/database/sqlalchemy-schema.v1.json"
    has_ci_gate = "python scripts/ci/check_sqlalchemy_schema_contract.py" in ci_source
    if not contract_path.is_file():
        return ReadinessCheck(
            name="sqlalchemy schema contract",
            passed=False,
            detail=f"missing contract: {contract_path}",
        )

    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    summary = contract.get("summary", {})
    tables = contract.get("tables", [])
    table_names = {table.get("name") for table in tables}
    required_tables = {
        "audit_log",
        "projects",
        "datasets",
        "training_runs",
        "model_versions",
        "deployment_revisions",
        "inference_request_logs",
        "drift_reports",
        "retraining_runs",
    }
    contract_current, contract_detail = verify_sqlalchemy_schema_contract(contract_path)
    has_table_depth = summary.get("table_count", 0) >= 38
    has_column_depth = summary.get("column_count", 0) >= 390
    has_foreign_key_depth = summary.get("foreign_key_count", 0) >= 60
    missing_tables = sorted(required_tables - table_names)
    has_indexed_foreign_keys = all(
        not column.get("foreign_keys")
        or column.get("index")
        or column.get("primary_key")
        for table in tables
        for column in table.get("columns", [])
    )
    passed = (
        has_ci_gate
        and contract_current
        and has_table_depth
        and has_column_depth
        and has_foreign_key_depth
        and not missing_tables
        and has_indexed_foreign_keys
    )
    return ReadinessCheck(
        name="sqlalchemy schema contract",
        passed=passed,
        detail=(
            "SQLAlchemy metadata contract, required tables, and indexed foreign keys are configured"
            if passed
            else (
                f"has_ci_gate={has_ci_gate}, "
                f"contract_current={contract_current}, "
                f"contract_detail={contract_detail}, "
                f"has_table_depth={has_table_depth}, "
                f"has_column_depth={has_column_depth}, "
                f"has_foreign_key_depth={has_foreign_key_depth}, "
                f"missing_tables={missing_tables}, "
                f"has_indexed_foreign_keys={has_indexed_foreign_keys}"
            )
        ),
    )


def check_frontend_supply_chain_contract(repo_root: Path) -> ReadinessCheck:
    ci_source = (repo_root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    package_lock = json.loads(
        (repo_root / "frontend/package-lock.json").read_text(encoding="utf-8")
    )
    packages = package_lock.get("packages", {})
    package_names = set(packages) if isinstance(packages, dict) else set()
    has_prod_audit_gate = "npm --prefix frontend audit --omit=dev" in ci_source
    vulnerable_router_packages = sorted(
        package_name
        for package_name in package_names
        if package_name in {"node_modules/react-router", "node_modules/react-router-dom"}
    )
    passed = has_prod_audit_gate and not vulnerable_router_packages
    return ReadinessCheck(
        name="frontend supply-chain contract",
        passed=passed,
        detail=(
            "frontend production dependencies are audited in CI"
            if passed
            else (
                f"has_prod_audit_gate={has_prod_audit_gate}, "
                f"vulnerable_router_packages={vulnerable_router_packages}"
            )
        ),
    )


def check_frontend_performance_contract(repo_root: Path) -> ReadinessCheck:
    ci_source = (repo_root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    app_source = (repo_root / "frontend/src/app/App.tsx").read_text(encoding="utf-8")
    routes_source = (repo_root / "frontend/src/app/routes.tsx").read_text(encoding="utf-8")
    has_budget_gate = "python scripts/ci/check_frontend_bundle_budget.py" in ci_source
    uses_suspense_boundary = "<Suspense fallback={<RouteLoadingState />}" in app_source
    lazy_route_imports = routes_source.count("lazy(() =>")
    passed = has_budget_gate and uses_suspense_boundary and lazy_route_imports >= 10
    return ReadinessCheck(
        name="frontend performance contract",
        passed=passed,
        detail=(
            "route-level code splitting and bundle budget gate are configured"
            if passed
            else (
                f"has_budget_gate={has_budget_gate}, "
                f"uses_suspense_boundary={uses_suspense_boundary}, "
                f"lazy_route_imports={lazy_route_imports}"
            )
        ),
    )


def check_readiness_probe_contract(repo_root: Path) -> ReadinessCheck:
    config_source = (repo_root / "backend/src/forgeml/platform/config.py").read_text(
        encoding="utf-8"
    )
    health_source = (repo_root / "backend/src/forgeml/platform/health.py").read_text(
        encoding="utf-8"
    )
    main_source = (repo_root / "backend/src/forgeml/main.py").read_text(encoding="utf-8")
    metrics_source = (
        repo_root / "backend/src/forgeml/platform/observability/metrics.py"
    ).read_text(encoding="utf-8")
    contract = json.loads(
        (repo_root / "contracts/openapi/forgeml.v1.openapi.json").read_text(encoding="utf-8")
    )
    ready_responses = contract["paths"]["/health/ready"]["get"].get("responses", {})
    required_fragments = {
        "FORGEML_READINESS_CHECKS_ENABLED": config_source,
        "FORGEML_READINESS_TIMEOUT_SECONDS": config_source,
        "DependencyProbe": health_source,
        "ReadinessChecker": health_source,
        "check_database_connection": health_source,
        "check_redis_connection": health_source,
        "readiness_probe_status": metrics_source,
        "readiness_probe_duration_seconds": metrics_source,
        "build_readiness_checker": main_source,
        "status_code=503": main_source,
    }
    missing_fragments = [
        fragment for fragment, source in required_fragments.items() if fragment not in source
    ]
    has_503_contract = "503" in ready_responses
    passed = not missing_fragments and has_503_contract
    return ReadinessCheck(
        name="readiness probe contract",
        passed=passed,
        detail=(
            "dependency readiness probes, metrics, and 503 API contract are configured"
            if passed
            else f"missing_fragments={missing_fragments}, has_503_contract={has_503_contract}"
        ),
    )


def check_openapi_contract(repo_root: Path) -> ReadinessCheck:
    ci_source = (repo_root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    contract = json.loads(
        (repo_root / "contracts/openapi/forgeml.v1.openapi.json").read_text(encoding="utf-8")
    )
    paths = set(contract.get("paths", {}))
    required_paths = {
        "/health/live",
        "/health/ready",
        "/api/v1/auth/login",
        "/api/v1/projects",
        "/api/v1/projects/{project_id}/datasets",
        "/api/v1/projects/{project_id}/training-runs",
        "/api/v1/models/{model_id}/versions/promote-training-run",
        "/api/v1/inference-endpoints/{endpoint_id}/predict",
        "/api/v1/projects/{project_id}/drift-reports",
        "/api/v1/retraining-policies/{policy_id}/trigger",
    }
    missing_paths = sorted(required_paths - paths)
    has_ci_gate = "python scripts/ci/generate_openapi_contract.py --check" in ci_source
    passed = has_ci_gate and not missing_paths
    return ReadinessCheck(
        name="openapi contract",
        passed=passed,
        detail=(
            "checked-in OpenAPI contract covers core API groups and is checked in CI"
            if passed
            else f"has_ci_gate={has_ci_gate}, missing_paths={missing_paths}"
        ),
    )


def check_problem_details_contract(repo_root: Path) -> ReadinessCheck:
    ci_source = (repo_root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    handlers_source = (repo_root / "backend/src/forgeml/platform/api/errors.py").read_text(
        encoding="utf-8"
    )
    problem_source = (
        repo_root / "backend/src/forgeml/platform/api/problem_details.py"
    ).read_text(encoding="utf-8")
    contract = json.loads(
        (repo_root / "contracts/api/problem-details.v1.json").read_text(encoding="utf-8")
    )
    required_fields = set(contract.get("required_fields", []))
    validation_fields = set(contract.get("validation_error_required_fields", []))
    handled_exception_types = set(contract.get("handled_exception_types", []))
    domain_error_codes = {error.get("code") for error in contract.get("domain_errors", [])}
    required_fragments = {
        "problem_details_response": handlers_source,
        "validation_problem_details": handlers_source,
        "http_problem_details": handlers_source,
        "internal_problem_details": handlers_source,
        "RequestValidationError": handlers_source,
        "StarletteHTTPException": handlers_source,
        "INTERNAL_ERROR_DETAIL": problem_source,
        "normalize_validation_errors": problem_source,
    }
    missing_fragments = [
        fragment for fragment, source in required_fragments.items() if fragment not in source
    ]
    has_ci_gate = "python scripts/ci/check_problem_details_contract.py" in ci_source
    has_required_fields = {
        "type",
        "title",
        "status",
        "detail",
        "trace_id",
        "errors",
    }.issubset(required_fields)
    has_validation_fields = {"loc", "msg", "type"}.issubset(validation_fields)
    has_exception_coverage = {
        "ForgeMLError",
        "RequestValidationError",
        "StarletteHTTPException",
        "Exception",
    }.issubset(handled_exception_types)
    has_domain_codes = {
        "authentication_failed",
        "permission_denied",
        "resource_not_found",
        "conflict",
        "validation_failed",
        "internal_error",
    }.issubset(domain_error_codes)
    passed = (
        has_ci_gate
        and not missing_fragments
        and has_required_fields
        and has_validation_fields
        and has_exception_coverage
        and has_domain_codes
    )
    return ReadinessCheck(
        name="problem details contract",
        passed=passed,
        detail=(
            "API error envelope, validation redaction, and exception handlers are checked in CI"
            if passed
            else (
                f"has_ci_gate={has_ci_gate}, "
                f"missing_fragments={missing_fragments}, "
                f"has_required_fields={has_required_fields}, "
                f"has_validation_fields={has_validation_fields}, "
                f"has_exception_coverage={has_exception_coverage}, "
                f"has_domain_codes={has_domain_codes}"
            )
        ),
    )


def check_api_authorization_contract(repo_root: Path) -> ReadinessCheck:
    ci_source = (repo_root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    contract = json.loads(
        (repo_root / "contracts/security/api-authorization.v1.json").read_text(encoding="utf-8")
    )
    public_routes = {
        (route.get("method"), route.get("path")) for route in contract.get("public_routes", [])
    }
    protected_routes = {
        (route.get("method"), route.get("path")) for route in contract.get("protected_routes", [])
    }
    required_public_routes = {
        ("GET", "/health/live"),
        ("GET", "/health/ready"),
        ("GET", "/metrics"),
        ("POST", "/api/v1/auth/login"),
        ("POST", "/api/v1/auth/refresh"),
        ("POST", "/api/v1/auth/logout"),
    }
    required_protected_routes = {
        ("GET", "/api/v1/auth/me"),
        ("GET", "/api/v1/projects"),
        ("POST", "/api/v1/projects/{project_id}/training-runs"),
        ("POST", "/api/v1/inference-endpoints/{endpoint_id}/predict"),
    }
    has_ci_gate = "python scripts/ci/check_api_authorization_contract.py" in ci_source
    missing_public = sorted(required_public_routes - public_routes)
    missing_protected = sorted(required_protected_routes - protected_routes)
    passed = has_ci_gate and not missing_public and not missing_protected
    return ReadinessCheck(
        name="api authorization contract",
        passed=passed,
        detail=(
            "public allowlist and protected route contract are checked in CI"
            if passed
            else (
                f"has_ci_gate={has_ci_gate}, "
                f"missing_public={missing_public}, "
                f"missing_protected={missing_protected}"
            )
        ),
    )


def check_permission_catalog_contract(repo_root: Path) -> ReadinessCheck:
    ci_source = (repo_root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    contract = json.loads(
        (repo_root / "contracts/security/permission-catalog.v1.json").read_text(encoding="utf-8")
    )
    permissions = {permission.get("code") for permission in contract.get("permissions", [])}
    roles = {role.get("code") for role in contract.get("role_presets", [])}
    required_permissions = {
        "projects:create",
        "projects:read",
        "training_runs:create",
        "training_runs:read",
        "model_versions:review",
        "deployments:rollback",
        "inference:predict",
        "admin:audit_log:read",
    }
    required_roles = {"platform_admin", "ml_engineer", "ml_operator", "ml_viewer"}
    has_ci_gate = "python scripts/ci/check_permission_catalog.py" in ci_source
    missing_permissions = sorted(required_permissions - permissions)
    missing_roles = sorted(required_roles - roles)
    passed = has_ci_gate and not missing_permissions and not missing_roles
    return ReadinessCheck(
        name="permission catalog contract",
        passed=passed,
        detail=(
            "permission vocabulary and role presets are checked in CI"
            if passed
            else (
                f"has_ci_gate={has_ci_gate}, "
                f"missing_permissions={missing_permissions}, "
                f"missing_roles={missing_roles}"
            )
        ),
    )


def check_runtime_config_policy_contract(repo_root: Path) -> ReadinessCheck:
    ci_source = (repo_root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    policy_source = (repo_root / "backend/src/forgeml/platform/config_policy.py").read_text(
        encoding="utf-8"
    )
    main_source = (repo_root / "backend/src/forgeml/main.py").read_text(encoding="utf-8")
    contract = json.loads(
        (repo_root / "contracts/security/runtime-config-policy.v1.json").read_text(
            encoding="utf-8"
        )
    )
    guardrails = {guardrail.get("code") for guardrail in contract.get("guardrails", [])}
    required_guardrails = {
        "jwt_secret_not_default",
        "jwt_secret_minimum_length",
        "docs_disabled",
        "rate_limit_enabled",
        "structured_logging_enabled",
        "request_logging_enabled",
        "readiness_checks_enabled",
        "cors_origins_non_empty",
        "cors_no_wildcard",
        "cors_no_localhost",
        "database_url_not_localhost",
        "redis_url_not_localhost",
        "object_storage_endpoint_not_localhost",
        "mlflow_tracking_uri_not_localhost",
        "airflow_base_url_not_localhost",
    }
    has_ci_gate = "python scripts/ci/check_runtime_config_policy.py" in ci_source
    app_enforces_policy = "assert_runtime_config_safe(resolved_settings)" in main_source
    production_like_declared = "PRODUCTION_LIKE_ENVIRONMENTS" in policy_source
    missing_guardrails = sorted(required_guardrails - guardrails)
    passed = (
        has_ci_gate
        and app_enforces_policy
        and production_like_declared
        and not missing_guardrails
    )
    return ReadinessCheck(
        name="runtime config policy contract",
        passed=passed,
        detail=(
            "production-like runtime guardrails are enforced at startup and checked in CI"
            if passed
            else (
                f"has_ci_gate={has_ci_gate}, "
                f"app_enforces_policy={app_enforces_policy}, "
                f"production_like_declared={production_like_declared}, "
                f"missing_guardrails={missing_guardrails}"
            )
        ),
    )


def check_request_logging_contract(repo_root: Path) -> ReadinessCheck:
    ci_source = (repo_root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    config_source = (repo_root / "backend/src/forgeml/platform/config.py").read_text(
        encoding="utf-8"
    )
    middleware_source = (
        repo_root / "backend/src/forgeml/platform/api/middleware.py"
    ).read_text(encoding="utf-8")
    logging_source = (
        repo_root / "backend/src/forgeml/platform/observability/logging.py"
    ).read_text(encoding="utf-8")
    contract = json.loads(
        (repo_root / "contracts/observability/request-log-event.v1.json").read_text(
            encoding="utf-8"
        )
    )
    required_top_level_fields = set(contract.get("required_top_level_fields", []))
    required_http_fields = set(contract.get("required_http_fields", []))
    has_ci_gate = "python scripts/ci/check_request_logging_contract.py" in ci_source
    required_fragments = {
        "FORGEML_STRUCTURED_LOGGING_ENABLED": config_source,
        "FORGEML_REQUEST_LOGGING_ENABLED": config_source,
        "RequestContextMiddleware": middleware_source,
        "build_http_request_log_event": middleware_source,
        "log_http_request": middleware_source,
        "JsonLogFormatter": logging_source,
        "redact_mapping": logging_source,
        "REQUEST_LOG_SCHEMA_VERSION": logging_source,
    }
    missing_fragments = [
        fragment for fragment, source in required_fragments.items() if fragment not in source
    ]
    has_required_event_fields = {
        "schema_version",
        "event_name",
        "service",
        "environment",
        "trace_id",
        "http",
    }.issubset(required_top_level_fields)
    has_required_http_fields = {
        "method",
        "route",
        "path",
        "status_code",
        "status_class",
        "duration_ms",
        "client_host",
        "query_params",
    }.issubset(required_http_fields)
    passed = (
        has_ci_gate
        and not missing_fragments
        and has_required_event_fields
        and has_required_http_fields
    )
    return ReadinessCheck(
        name="request logging contract",
        passed=passed,
        detail=(
            "structured request logging, redaction, and contract gate are configured"
            if passed
            else (
                f"has_ci_gate={has_ci_gate}, "
                f"missing_fragments={missing_fragments}, "
                f"has_required_event_fields={has_required_event_fields}, "
                f"has_required_http_fields={has_required_http_fields}"
            )
        ),
    )


def _scan_file(path: Path, repo_root: Path, findings: list[str]) -> None:
    if path.suffix in {".png", ".jpg", ".jpeg", ".gif", ".ico"}:
        return
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return
    for line_number, line in enumerate(text.splitlines(), start=1):
        if any(token in line for token in BANNED_TOKENS):
            findings.append(f"{path.relative_to(repo_root)}:{line_number}")


def main() -> int:
    checks = run_checks()
    for check in checks:
        status = "PASS" if check.passed else "FAIL"
        print(f"{status} {check.name}: {check.detail}")
    return 0 if all(check.passed for check in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
