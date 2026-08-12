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


def test_alembic_migration_contract_gate_is_enforced() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    contract = json.loads(
        Path("contracts/database/alembic-migrations.v1.json").read_text(encoding="utf-8")
    )
    migrations = contract["migrations"]

    assert "python scripts/ci/check_alembic_migration_contract.py" in workflow
    assert contract["schema_version"] == "forgeml.alembic_migrations.v1"
    assert contract["summary"]["base_revision"] == "202607180001"
    assert contract["summary"]["head_revision"] == "202607190015"
    assert contract["summary"]["head_count"] == 1
    assert len(migrations) >= 14
    assert all(migration["has_upgrade"] and migration["has_downgrade"] for migration in migrations)


def test_sqlalchemy_schema_contract_gate_is_enforced() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    contract = json.loads(
        Path("contracts/database/sqlalchemy-schema.v1.json").read_text(encoding="utf-8")
    )
    table_names = {table["name"] for table in contract["tables"]}

    assert "python scripts/ci/check_sqlalchemy_schema_contract.py" in workflow
    assert contract["schema_version"] == "forgeml.sqlalchemy_schema.v1"
    assert contract["summary"]["table_count"] >= 38
    assert contract["summary"]["foreign_key_count"] >= 60
    assert {
        "audit_log",
        "projects",
        "training_runs",
        "model_versions",
        "retraining_runs",
    }.issubset(table_names)


def test_artifact_manifest_contract_gate_is_enforced() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    contract = json.loads(
        Path("contracts/artifacts/artifact-manifest.v1.json").read_text(encoding="utf-8")
    )
    producer_types = {producer["artifact_set_type"] for producer in contract["producers"]}

    assert "python scripts/ci/check_artifact_manifest_contract.py" in workflow
    assert contract["schema_version"] == "forgeml.artifact_manifest_contract.v1"
    assert contract["manifest_schema_version"] == "forgeml.artifact_manifest.v1"
    assert contract["checksum_policy"]["algorithm"] == "sha256"
    assert contract["storage_contract"]["writer_protocol"] == "ArtifactManifestWriter"
    assert "checksum_sha256" in contract["required_artifact_fields"]
    assert {"dataset_version", "model_version"}.issubset(producer_types)


def test_mlflow_tracking_contract_gate_is_enforced() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    contract = json.loads(
        Path("contracts/mlflow/mlflow-tracking.v1.json").read_text(encoding="utf-8")
    )
    tracking_source = Path("backend/src/forgeml/platform/mlflow/tracking.py").read_text(
        encoding="utf-8"
    )

    assert "python scripts/ci/check_mlflow_tracking_contract.py" in workflow
    assert contract["schema_version"] == "forgeml.mlflow_tracking_contract.v1"
    assert contract["sync_schema_version"] == "forgeml.mlflow_tracking_sync.v1"
    assert contract["tracking_boundary"]["gateway_protocol"] == "MLflowTrackingGateway"
    assert "/api/2.0/mlflow/runs/log-batch" in contract["rest_endpoints"]
    assert "forgeml.training_run_id" in contract["required_tags"]
    assert "MLflowHttpTrackingGateway" in tracking_source


def test_airflow_orchestration_contract_gate_is_enforced() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    contract = json.loads(
        Path("contracts/orchestration/airflow-training.v1.json").read_text(
            encoding="utf-8"
        )
    )
    orchestrator_source = Path(
        "backend/src/forgeml/modules/training/infrastructure/orchestrator.py"
    ).read_text(encoding="utf-8")

    assert "python scripts/ci/check_airflow_orchestration_contract.py" in workflow
    assert contract["schema_version"] == "forgeml.airflow_training_orchestration_contract.v1"
    assert contract["airflow_schema_version"] == "forgeml.airflow_orchestration.v1"
    assert contract["training_conf_schema_version"] == "forgeml.training_airflow_dag_run.v1"
    assert contract["gateway_boundary"]["gateway_protocol"] == "AirflowWorkflowGateway"
    assert contract["gateway_boundary"]["local_fallback"] == "LocalTrainingWorkflowOrchestrator"
    assert contract["status_mapping"]["success"] == "succeeded"
    assert "AirflowTrainingWorkflowOrchestrator" in orchestrator_source


def test_deployment_runtime_contract_gate_is_enforced() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    contract = json.loads(
        Path("contracts/runtime/deployment-serving.v1.json").read_text(encoding="utf-8")
    )
    serving_source = Path("backend/src/forgeml/platform/serving/runtime.py").read_text(
        encoding="utf-8"
    )

    assert "python scripts/ci/check_deployment_runtime_contract.py" in workflow
    assert contract["schema_version"] == "forgeml.deployment_runtime_contract.v1"
    assert contract["serving_runtime_schema_version"] == "forgeml.serving_runtime.v1"
    assert contract["adapter_boundary"]["gateway_protocol"] == "ServingRuntimeGateway"
    assert "rollback" in contract["traffic_semantics"]
    assert "InMemoryServingRuntimeGateway" in serving_source


def test_monitoring_dashboard_contract_gate_is_enforced() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    contract = json.loads(
        Path("contracts/observability/monitoring-dashboard.v1.json").read_text(
            encoding="utf-8"
        )
    )
    monitoring_page = Path(
        "frontend/src/modules/monitoring/pages/MonitoringPage.tsx"
    ).read_text(encoding="utf-8")

    assert "python scripts/ci/check_monitoring_dashboard_contract.py" in workflow
    assert contract["schema_version"] == "forgeml.monitoring_dashboard_contract.v1"
    assert "GET /api/v1/projects/{project_id}/monitoring/operations" in contract["api_surface"]
    assert "training_failures" in contract["operations_signal_families"]
    assert "retraining_activity" in contract["operations_signal_families"]
    assert "Latency Percentiles" in monitoring_page
    assert "Retraining Activity" in monitoring_page


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


def test_security_hardening_contract_gate_is_enforced() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    contract = json.loads(
        Path("contracts/security/security-hardening.v1.json").read_text(encoding="utf-8")
    )
    audit_source = Path(
        "backend/src/forgeml/modules/administration/application/audit.py"
    ).read_text(encoding="utf-8")

    assert "python scripts/ci/check_security_hardening_contract.py" in workflow
    assert contract["schema_version"] == "forgeml.security_hardening_contract.v1"
    assert "organization_isolation" in contract["control_families"]
    assert "rbac_role_matrix" in contract["control_families"]
    assert "rate_limit_partitioning" in contract["control_families"]
    assert "audit_log" in contract["tenant_isolation_sources"]
    assert "security_auditor" in contract["rbac_role_presets"]
    assert "password" in contract["sensitive_audit_metadata_keys"]
    assert "SENSITIVE_AUDIT_METADATA_KEYS" in audit_source


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


def test_release_smoke_contract_gate_is_enforced() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    runbook = Path("docs/runbooks/production-readiness.md").read_text(encoding="utf-8")
    contract = json.loads(Path("contracts/ops/release-smoke.v1.json").read_text(encoding="utf-8"))
    smoke_source = Path("scripts/ops/release_smoke.py").read_text(encoding="utf-8")
    stage_codes = {stage["code"] for stage in contract["stages"]}

    assert "python scripts/ci/check_release_smoke_contract.py" in workflow
    assert "scripts/ops/release_smoke.py --base-url" in runbook
    assert contract["schema_version"] == "forgeml.release_smoke_contract.v1"
    assert contract["runtime_requirements"]["mutates_data"] is False
    assert contract["summary"]["required_stage_count"] >= 16
    assert "training_logs_surface" in stage_codes
    assert "/api/v1/projects/{project_id}/monitoring/summary" in smoke_source


def test_release_manifest_contract_gate_is_enforced() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    runbook = Path("docs/runbooks/production-readiness.md").read_text(encoding="utf-8")
    contract = json.loads(
        Path("contracts/ops/release-manifest.v1.json").read_text(encoding="utf-8")
    )
    manifest_source = Path("scripts/ops/build_release_manifest.py").read_text(encoding="utf-8")
    artifact_paths = {artifact["path"] for artifact in contract["artifact_definitions"]}
    image_names = {image["name"] for image in contract["image_targets"]}

    assert "python scripts/ci/check_release_manifest_contract.py" in workflow
    assert "scripts/ops/build_release_manifest.py --output" in runbook
    assert contract["schema_version"] == "forgeml.release_manifest_contract.v1"
    assert contract["manifest_schema_version"] == "forgeml.release_manifest.v1"
    assert contract["summary"]["required_artifact_count"] >= 14
    assert "contracts/openapi/forgeml.v1.openapi.json" in artifact_paths
    assert "contracts/artifacts/artifact-manifest.v1.json" in artifact_paths
    assert "contracts/mlflow/mlflow-tracking.v1.json" in artifact_paths
    assert "contracts/orchestration/airflow-training.v1.json" in artifact_paths
    assert "contracts/observability/monitoring-dashboard.v1.json" in artifact_paths
    assert "contracts/security/security-hardening.v1.json" in artifact_paths
    assert "contracts/ops/release-smoke.v1.json" in artifact_paths
    assert "contracts/ops/release-evidence-workflow.v1.json" in artifact_paths
    assert "contracts/ops/release-manifest-verification.v1.json" in artifact_paths
    assert {"backend", "frontend", "training", "inference", "airflow"}.issubset(image_names)
    assert "_sha256_file" in manifest_source


def test_release_evidence_workflow_contract_gate_is_enforced() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    contract = json.loads(
        Path("contracts/ops/release-evidence-workflow.v1.json").read_text(
            encoding="utf-8"
        )
    )

    assert "python scripts/ci/check_release_evidence_workflow.py" in workflow
    assert "release-evidence:" in workflow
    assert "needs: [backend, frontend, docker, production-readiness]" in workflow
    assert "actions/upload-artifact@v4" in workflow
    assert "if-no-files-found: error" in workflow
    assert contract["schema_version"] == "forgeml.release_evidence_workflow.v1"
    assert contract["artifact_name"] == "forgeml-release-manifest"
    assert contract["manifest_path"] == "dist/release/forgeml-release-manifest.json"


def test_release_manifest_verifier_contract_gate_is_enforced() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    runbook = Path("docs/runbooks/production-readiness.md").read_text(encoding="utf-8")
    contract = json.loads(
        Path("contracts/ops/release-manifest-verification.v1.json").read_text(
            encoding="utf-8"
        )
    )
    verifier_source = Path("scripts/ops/verify_release_manifest.py").read_text(
        encoding="utf-8"
    )

    assert "python scripts/ci/check_release_manifest_verifier_contract.py" in workflow
    assert "python scripts/ops/verify_release_manifest.py" in workflow
    assert "--require-ci-evidence" in workflow
    assert "scripts/ops/verify_release_manifest.py --manifest" in runbook
    assert contract["schema_version"] == "forgeml.release_manifest_verification_contract.v1"
    assert contract["verification_schema_version"] == "forgeml.release_manifest_verification.v1"
    assert "artifact_hash_integrity" in contract["required_checks"]
    assert "dockerfile_hash_integrity" in contract["required_checks"]
    assert "_sha256_file" in verifier_source
