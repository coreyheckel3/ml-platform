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

from forgeml.platform.mlflow import MLFLOW_TRACKING_SYNC_SCHEMA_VERSION  # noqa: E402

MLFLOW_TRACKING_CONTRACT_SCHEMA_VERSION = "forgeml.mlflow_tracking_contract.v1"
DEFAULT_OUTPUT_PATH = Path("contracts/mlflow/mlflow-tracking.v1.json")
DEFAULT_CI_PATH = Path(".github/workflows/ci.yml")


def build_mlflow_tracking_contract() -> dict[str, Any]:
    return {
        "schema_version": MLFLOW_TRACKING_CONTRACT_SCHEMA_VERSION,
        "sync_schema_version": MLFLOW_TRACKING_SYNC_SCHEMA_VERSION,
        "generated_from": [
            "forgeml.platform.mlflow.tracking",
            "forgeml.modules.training.application.services",
            "forgeml.modules.training.api.routes",
            "scripts.workers.run_training_worker",
        ],
        "tracking_boundary": {
            "gateway_protocol": "MLflowTrackingGateway",
            "http_adapter": "MLflowHttpTrackingGateway",
            "local_test_adapter": "InMemoryMLflowTrackingGateway",
            "disabled_adapter": "DisabledMLflowTrackingGateway",
            "factory": "build_mlflow_tracking_gateway",
            "runtime_dependency_policy": "stdlib-http-adapter",
        },
        "rest_endpoints": [
            "/api/2.0/mlflow/experiments/get-by-name",
            "/api/2.0/mlflow/experiments/create",
            "/api/2.0/mlflow/runs/create",
            "/api/2.0/mlflow/runs/log-batch",
            "/api/2.0/mlflow/runs/update",
        ],
        "required_record_fields": [
            "experiment_name",
            "run_name",
            "organization_id",
            "project_id",
            "experiment_id",
            "experiment_run_id",
            "training_run_id",
            "status",
            "artifact_uri",
            "parameters",
            "metrics",
            "tags",
            "artifacts",
        ],
        "required_sync_result_fields": [
            "schema_version",
            "tracking_uri",
            "experiment_name",
            "run_id",
            "status",
            "logged_param_count",
            "logged_metric_count",
            "logged_artifact_count",
            "error_message",
            "created_at",
        ],
        "required_tags": [
            "forgeml.organization_id",
            "forgeml.project_id",
            "forgeml.experiment_id",
            "forgeml.experiment_run_id",
            "forgeml.training_run_id",
            "forgeml.status",
            "forgeml.artifact_uri",
        ],
        "artifact_logging_policy": {
            "mode": "artifact_reference_tags",
            "required_tag_patterns": [
                "forgeml.artifact.count",
                "forgeml.artifact.<name>.uri",
                "forgeml.artifact.<name>.type",
                "forgeml.artifact.<name>.media_type",
            ],
        },
        "failure_semantics": {
            "training_lifecycle": "best_effort_tracking_sync",
            "failed_sync_effect": "training_terminal_status_is_preserved",
            "observability": [
                "forgeml_mlflow_tracking_sync_total",
                "training.mlflow logs",
                "mlflow_sync events",
                "evaluation_report.mlflow_sync",
            ],
        },
        "configuration": [
            "FORGEML_MLFLOW_TRACKING_URI",
            "FORGEML_MLFLOW_SYNC_ENABLED",
            "FORGEML_MLFLOW_EXPERIMENT_PREFIX",
            "FORGEML_MLFLOW_HTTP_TIMEOUT_SECONDS",
        ],
        "quality_gates": [
            "python scripts/ci/check_mlflow_tracking_contract.py",
            "backend/tests/unit/platform/test_mlflow_tracking.py",
            "backend/tests/unit/training/test_training_service.py",
            "backend/tests/unit/ops/test_mlflow_tracking_contract.py",
        ],
    }


def serialize_mlflow_tracking_contract(contract: dict[str, Any]) -> str:
    return json.dumps(contract, indent=2, sort_keys=True) + "\n"


def write_mlflow_tracking_contract(output_path: Path = DEFAULT_OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        serialize_mlflow_tracking_contract(build_mlflow_tracking_contract()),
        encoding="utf-8",
    )


def check_mlflow_tracking_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    *,
    ci_path: Path = DEFAULT_CI_PATH,
    repo_root: Path = REPO_ROOT,
) -> tuple[bool, str]:
    findings = list(validate_mlflow_tracking_definition(repo_root))
    if not output_path.is_file():
        findings.append(f"MLflow tracking contract does not exist: {output_path}")
    else:
        expected = serialize_mlflow_tracking_contract(build_mlflow_tracking_contract())
        actual = output_path.read_text(encoding="utf-8")
        if actual != expected:
            findings.append(f"MLflow tracking contract is stale: {output_path}")

    if not ci_path.is_file():
        findings.append(f"CI workflow does not exist: {ci_path}")
    else:
        ci_source = ci_path.read_text(encoding="utf-8")
        if "python scripts/ci/check_mlflow_tracking_contract.py" not in ci_source:
            findings.append("MLflow tracking contract checker is not wired into CI.")

    if findings:
        return False, "MLflow tracking contract violations: " + "; ".join(findings)
    return True, f"MLflow tracking contract is current: {output_path}"


def validate_mlflow_tracking_definition(repo_root: Path = REPO_ROOT) -> tuple[str, ...]:
    required_files = [
        "backend/src/forgeml/platform/mlflow/tracking.py",
        "backend/src/forgeml/platform/mlflow/__init__.py",
        "backend/src/forgeml/modules/training/application/services.py",
        "backend/src/forgeml/modules/training/api/routes.py",
        "scripts/workers/run_training_worker.py",
        "backend/tests/unit/platform/test_mlflow_tracking.py",
        "backend/tests/unit/training/test_training_service.py",
        "backend/tests/unit/ops/test_mlflow_tracking_contract.py",
        ".env.example",
        "infra/compose/docker-compose.yml",
    ]
    findings = [
        f"Missing MLflow tracking source file: {path}"
        for path in required_files
        if not (repo_root / path).is_file()
    ]
    if findings:
        return tuple(findings)

    sources = {
        path: (repo_root / path).read_text(encoding="utf-8") for path in required_files
    }
    required_fragments = (
        (
            MLFLOW_TRACKING_SYNC_SCHEMA_VERSION,
            sources["backend/src/forgeml/platform/mlflow/tracking.py"],
        ),
        (
            "MLflowTrackingGateway",
            sources["backend/src/forgeml/platform/mlflow/tracking.py"],
        ),
        (
            "MLflowHttpTrackingGateway",
            sources["backend/src/forgeml/platform/mlflow/tracking.py"],
        ),
        (
            "InMemoryMLflowTrackingGateway",
            sources["backend/src/forgeml/platform/mlflow/tracking.py"],
        ),
        (
            "DisabledMLflowTrackingGateway",
            sources["backend/src/forgeml/platform/mlflow/tracking.py"],
        ),
        (
            "build_training_run_mlflow_record",
            sources["backend/src/forgeml/platform/mlflow/tracking.py"],
        ),
        (
            "build_mlflow_tracking_gateway",
            sources["backend/src/forgeml/platform/mlflow/tracking.py"],
        ),
        (
            "/api/2.0/mlflow/runs/log-batch",
            sources["backend/src/forgeml/platform/mlflow/tracking.py"],
        ),
        ("forgeml.artifact.", sources["backend/src/forgeml/platform/mlflow/tracking.py"]),
        (
            "mlflow_tracking",
            sources["backend/src/forgeml/modules/training/application/services.py"],
        ),
        (
            "_sync_mlflow_tracking",
            sources["backend/src/forgeml/modules/training/application/services.py"],
        ),
        (
            "mlflow_tracking_sync_total",
            sources["backend/src/forgeml/modules/training/application/services.py"],
        ),
        (
            "evaluation_report.mlflow_sync",
            serialize_mlflow_tracking_contract(build_mlflow_tracking_contract()),
        ),
        (
            "build_mlflow_tracking_gateway",
            sources["backend/src/forgeml/modules/training/api/routes.py"],
        ),
        (
            "build_mlflow_tracking_gateway",
            sources["scripts/workers/run_training_worker.py"],
        ),
        ("FORGEML_MLFLOW_SYNC_ENABLED", sources[".env.example"]),
        ("FORGEML_MLFLOW_EXPERIMENT_PREFIX", sources[".env.example"]),
        ("FORGEML_MLFLOW_HTTP_TIMEOUT_SECONDS", sources[".env.example"]),
        ("mlflow", sources["infra/compose/docker-compose.yml"]),
    )
    missing_fragments = sorted(
        fragment for fragment, source in required_fragments if fragment not in source
    )
    if missing_fragments:
        findings.append(f"Missing MLflow tracking fragments: {missing_fragments}")

    contract = build_mlflow_tracking_contract()
    if contract["sync_schema_version"] != MLFLOW_TRACKING_SYNC_SCHEMA_VERSION:
        findings.append("MLflow sync schema version is inconsistent.")
    if len(contract["rest_endpoints"]) < 5:
        findings.append("MLflow tracking contract must include REST endpoint coverage.")
    if "forgeml.training_run_id" not in contract["required_tags"]:
        findings.append("MLflow tracking contract must require training run lineage tags.")

    return tuple(findings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify the ForgeML MLflow tracking integration contract."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the checked-in MLflow tracking contract.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate the checked-in MLflow tracking contract.",
    )
    args = parser.parse_args(argv)

    if args.write:
        write_mlflow_tracking_contract(args.output)
        print(f"Wrote MLflow tracking contract: {args.output}")
        return 0

    passed, detail = check_mlflow_tracking_contract(args.output)
    print(("PASS " if passed else "FAIL ") + detail)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
