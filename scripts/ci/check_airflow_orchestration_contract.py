from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_SRC = REPO_ROOT / "backend/src"
for import_path in (REPO_ROOT, BACKEND_SRC):
    import_path_value = str(import_path)
    if import_path_value not in sys.path:
        sys.path.insert(0, import_path_value)

from forgeml.modules.training.infrastructure.orchestrator import (  # noqa: E402
    TRAINING_AIRFLOW_CONF_SCHEMA_VERSION,
)
from forgeml.platform.airflow import AIRFLOW_ORCHESTRATION_SCHEMA_VERSION  # noqa: E402

AIRFLOW_ORCHESTRATION_CONTRACT_SCHEMA_VERSION = (
    "forgeml.airflow_training_orchestration_contract.v1"
)
DEFAULT_OUTPUT_PATH = Path("contracts/orchestration/airflow-training.v1.json")
DEFAULT_CI_PATH = Path(".github/workflows/ci.yml")


def build_airflow_orchestration_contract() -> dict[str, Any]:
    return {
        "schema_version": AIRFLOW_ORCHESTRATION_CONTRACT_SCHEMA_VERSION,
        "airflow_schema_version": AIRFLOW_ORCHESTRATION_SCHEMA_VERSION,
        "training_conf_schema_version": TRAINING_AIRFLOW_CONF_SCHEMA_VERSION,
        "generated_from": [
            "forgeml.platform.airflow.workflows",
            "forgeml.modules.training.infrastructure.orchestrator",
            "forgeml.modules.training.application.services",
            "forgeml.modules.training.api.routes",
            "scripts.workers.run_training_worker",
        ],
        "gateway_boundary": {
            "gateway_protocol": "AirflowWorkflowGateway",
            "http_adapter": "AirflowHttpWorkflowGateway",
            "local_test_adapter": "InMemoryAirflowWorkflowGateway",
            "training_adapter": "AirflowTrainingWorkflowOrchestrator",
            "local_fallback": "LocalTrainingWorkflowOrchestrator",
            "factory": "build_training_workflow_orchestrator",
            "runtime_dependency_policy": "stdlib-http-adapter",
        },
        "rest_endpoints": [
            "POST /api/v1/dags/{dag_id}/dagRuns",
            "GET /api/v1/dags/{dag_id}/dagRuns/{dag_run_id}",
            "PATCH /api/v1/dags/{dag_id}/dagRuns/{dag_run_id}",
        ],
        "training_dag_contract": {
            "dag_id_setting": "FORGEML_AIRFLOW_TRAINING_DAG_ID",
            "orchestrator_run_id_format": "airflow://{dag_id}/{dag_run_id}",
            "dag_run_id_format": "forgeml_training__{training_run_id}",
            "required_conf_fields": [
                "schema_version",
                "organization_id",
                "project_id",
                "experiment_id",
                "experiment_run_id",
                "training_run_id",
                "dataset_version_id",
                "feature_set_id",
                "algorithm",
                "model_type",
                "objective_metric_name",
                "hyperparameters",
                "artifact_uri",
                "requested_by",
            ],
        },
        "status_mapping": {
            "queued": "queued",
            "scheduled": "queued",
            "running": "running",
            "restarting": "running",
            "success": "succeeded",
            "failed": "failed",
            "upstream_failed": "failed",
            "skipped": "canceled",
            "removed": "canceled",
        },
        "api_surface": [
            "GET /api/v1/training-runs/{training_run_id}/orchestration-status",
        ],
        "configuration": [
            "FORGEML_AIRFLOW_BASE_URL",
            "FORGEML_AIRFLOW_ORCHESTRATION_ENABLED",
            "FORGEML_AIRFLOW_TRAINING_DAG_ID",
            "FORGEML_AIRFLOW_USERNAME",
            "FORGEML_AIRFLOW_PASSWORD",
            "FORGEML_AIRFLOW_HTTP_TIMEOUT_SECONDS",
        ],
        "quality_gates": [
            "python scripts/ci/check_airflow_orchestration_contract.py",
            "backend/tests/unit/platform/test_airflow_workflows.py",
            "backend/tests/unit/training/test_training_orchestrator.py",
            "backend/tests/unit/ops/test_airflow_orchestration_contract.py",
            "backend/tests/api/test_training_api.py",
        ],
    }


def serialize_airflow_orchestration_contract(contract: dict[str, Any]) -> str:
    return json.dumps(contract, indent=2, sort_keys=True) + "\n"


def write_airflow_orchestration_contract(output_path: Path = DEFAULT_OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        serialize_airflow_orchestration_contract(build_airflow_orchestration_contract()),
        encoding="utf-8",
    )


def check_airflow_orchestration_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    *,
    ci_path: Path = DEFAULT_CI_PATH,
    repo_root: Path = REPO_ROOT,
) -> tuple[bool, str]:
    findings = list(validate_airflow_orchestration_definition(repo_root))
    if not output_path.is_file():
        findings.append(f"Airflow orchestration contract does not exist: {output_path}")
    else:
        expected = serialize_airflow_orchestration_contract(
            build_airflow_orchestration_contract()
        )
        actual = output_path.read_text(encoding="utf-8")
        if actual != expected:
            findings.append(f"Airflow orchestration contract is stale: {output_path}")

    if not ci_path.is_file():
        findings.append(f"CI workflow does not exist: {ci_path}")
    else:
        ci_source = ci_path.read_text(encoding="utf-8")
        if "python scripts/ci/check_airflow_orchestration_contract.py" not in ci_source:
            findings.append("Airflow orchestration contract checker is not wired into CI.")

    if findings:
        return False, "Airflow orchestration contract violations: " + "; ".join(findings)
    return True, f"Airflow orchestration contract is current: {output_path}"


def validate_airflow_orchestration_definition(repo_root: Path = REPO_ROOT) -> tuple[str, ...]:
    required_files = [
        "backend/src/forgeml/platform/airflow/workflows.py",
        "backend/src/forgeml/platform/airflow/__init__.py",
        "backend/src/forgeml/modules/training/infrastructure/orchestrator.py",
        "backend/src/forgeml/modules/training/application/services.py",
        "backend/src/forgeml/modules/training/api/routes.py",
        "backend/src/forgeml/modules/training/api/schemas.py",
        "scripts/workers/run_training_worker.py",
        "backend/tests/unit/platform/test_airflow_workflows.py",
        "backend/tests/unit/training/test_training_orchestrator.py",
        "backend/tests/unit/ops/test_airflow_orchestration_contract.py",
        "backend/tests/api/test_training_api.py",
        ".env.example",
        "infra/docker/airflow.Dockerfile",
        "pipelines/airflow/dags/forgeml_training_pipeline.py",
    ]
    findings = [
        f"Missing Airflow orchestration source file: {path}"
        for path in required_files
        if not (repo_root / path).is_file()
    ]
    if findings:
        return tuple(findings)

    sources = {
        path: (repo_root / path).read_text(encoding="utf-8") for path in required_files
    }
    contract = serialize_airflow_orchestration_contract(build_airflow_orchestration_contract())
    required_fragments = (
        ("AirflowWorkflowGateway", sources["backend/src/forgeml/platform/airflow/workflows.py"]),
        (
            "AirflowHttpWorkflowGateway",
            sources["backend/src/forgeml/platform/airflow/workflows.py"],
        ),
        (
            "InMemoryAirflowWorkflowGateway",
            sources["backend/src/forgeml/platform/airflow/workflows.py"],
        ),
        (
            "/api/v1/dags/",
            sources["backend/src/forgeml/platform/airflow/workflows.py"],
        ),
        (
            "TRAINING_AIRFLOW_CONF_SCHEMA_VERSION",
            sources["backend/src/forgeml/modules/training/infrastructure/orchestrator.py"],
        ),
        (
            "AirflowTrainingWorkflowOrchestrator",
            sources["backend/src/forgeml/modules/training/infrastructure/orchestrator.py"],
        ),
        (
            "LocalTrainingWorkflowOrchestrator",
            sources["backend/src/forgeml/modules/training/infrastructure/orchestrator.py"],
        ),
        (
            "build_training_workflow_orchestrator",
            sources["backend/src/forgeml/modules/training/infrastructure/orchestrator.py"],
        ),
        (
            "map_airflow_state_to_training_status",
            sources["backend/src/forgeml/modules/training/infrastructure/orchestrator.py"],
        ),
        (
            "get_orchestration_status",
            sources["backend/src/forgeml/modules/training/application/services.py"],
        ),
        (
            "/orchestration-status",
            sources["backend/src/forgeml/modules/training/api/routes.py"],
        ),
        (
            "TrainingOrchestrationStatusResponse",
            sources["backend/src/forgeml/modules/training/api/schemas.py"],
        ),
        (
            "build_training_workflow_orchestrator",
            sources["scripts/workers/run_training_worker.py"],
        ),
        ("FORGEML_AIRFLOW_ORCHESTRATION_ENABLED", sources[".env.example"]),
        ("FORGEML_AIRFLOW_TRAINING_DAG_ID", sources[".env.example"]),
        ("FORGEML_AIRFLOW_HTTP_TIMEOUT_SECONDS", sources[".env.example"]),
        ("apache/airflow", sources["infra/docker/airflow.Dockerfile"]),
        (
            "forgeml_training_pipeline",
            sources["pipelines/airflow/dags/forgeml_training_pipeline.py"],
        ),
        (
            "forgeml.training_airflow_dag_run.v1",
            sources["pipelines/airflow/dags/forgeml_training_pipeline.py"],
        ),
        ("dataset_version_id", sources["pipelines/airflow/dags/forgeml_training_pipeline.py"]),
        ("feature_set_id", sources["pipelines/airflow/dags/forgeml_training_pipeline.py"]),
        ("forgeml_training__{training_run_id}", contract),
    )
    missing_fragments = sorted(
        fragment for fragment, source in required_fragments if fragment not in source
    )
    if missing_fragments:
        findings.append(f"Missing Airflow orchestration fragments: {missing_fragments}")

    airflow_contract = build_airflow_orchestration_contract()
    if airflow_contract["airflow_schema_version"] != AIRFLOW_ORCHESTRATION_SCHEMA_VERSION:
        findings.append("Airflow orchestration schema version is inconsistent.")
    if (
        airflow_contract["training_conf_schema_version"]
        != TRAINING_AIRFLOW_CONF_SCHEMA_VERSION
    ):
        findings.append("Training Airflow conf schema version is inconsistent.")
    if len(airflow_contract["rest_endpoints"]) < 3:
        findings.append("Airflow orchestration contract must include REST endpoint coverage.")
    if "training_run_id" not in airflow_contract["training_dag_contract"]["required_conf_fields"]:
        findings.append("Airflow training DAG contract must require training run lineage.")

    return tuple(findings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify the ForgeML Airflow training orchestration contract."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the checked-in Airflow orchestration contract.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate the checked-in Airflow orchestration contract.",
    )
    args = parser.parse_args(argv)

    if args.write:
        write_airflow_orchestration_contract(args.output)
        print(f"Wrote Airflow orchestration contract: {args.output}")
        return 0

    passed, detail = check_airflow_orchestration_contract(args.output)
    print(("PASS " if passed else "FAIL ") + detail)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
