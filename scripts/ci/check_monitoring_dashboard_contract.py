from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

MONITORING_DASHBOARD_CONTRACT_SCHEMA_VERSION = "forgeml.monitoring_dashboard_contract.v1"
DEFAULT_OUTPUT_PATH = Path("contracts/observability/monitoring-dashboard.v1.json")
DEFAULT_CI_PATH = Path(".github/workflows/ci.yml")
REPO_ROOT = Path(__file__).resolve().parents[2]


def build_monitoring_dashboard_contract() -> dict[str, Any]:
    return {
        "schema_version": MONITORING_DASHBOARD_CONTRACT_SCHEMA_VERSION,
        "generated_from": [
            "forgeml.modules.monitoring.domain.entities",
            "forgeml.modules.monitoring.application.services",
            "forgeml.modules.monitoring.infrastructure.sqlalchemy_repositories",
            "forgeml.modules.monitoring.api.routes",
            "frontend.src.modules.monitoring.pages.MonitoringPage",
        ],
        "api_surface": [
            "GET /api/v1/projects/{project_id}/monitoring/summary",
            "GET /api/v1/projects/{project_id}/monitoring/operations",
            "GET /api/v1/projects/{project_id}/monitoring/inference-endpoints",
        ],
        "operations_signal_families": [
            "inference_latency_percentiles",
            "inference_error_breakdown",
            "drift_trends",
            "training_failures",
            "retraining_activity",
        ],
        "frontend_sections": [
            "Latency Percentiles",
            "Inference Errors",
            "Drift Trends",
            "Training Failures",
            "Retraining Activity",
            "Endpoint Drilldown",
            "Alert Evaluation",
        ],
        "quality_gates": [
            "python scripts/ci/check_monitoring_dashboard_contract.py",
            "backend/tests/unit/monitoring/test_monitoring_service.py",
            "backend/tests/api/test_monitoring_api.py",
            "frontend/src/modules/monitoring/pages/MonitoringPage.test.tsx",
        ],
    }


def serialize_monitoring_dashboard_contract(contract: dict[str, Any]) -> str:
    return json.dumps(contract, indent=2, sort_keys=True) + "\n"


def write_monitoring_dashboard_contract(output_path: Path = DEFAULT_OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        serialize_monitoring_dashboard_contract(build_monitoring_dashboard_contract()),
        encoding="utf-8",
    )


def check_monitoring_dashboard_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    *,
    ci_path: Path = DEFAULT_CI_PATH,
    repo_root: Path = REPO_ROOT,
) -> tuple[bool, str]:
    findings = list(validate_monitoring_dashboard_definition(repo_root))
    if not output_path.is_file():
        findings.append(f"Monitoring dashboard contract does not exist: {output_path}")
    else:
        expected = serialize_monitoring_dashboard_contract(
            build_monitoring_dashboard_contract()
        )
        actual = output_path.read_text(encoding="utf-8")
        if actual != expected:
            findings.append(f"Monitoring dashboard contract is stale: {output_path}")

    if not ci_path.is_file():
        findings.append(f"CI workflow does not exist: {ci_path}")
    else:
        ci_source = ci_path.read_text(encoding="utf-8")
        if "python scripts/ci/check_monitoring_dashboard_contract.py" not in ci_source:
            findings.append("Monitoring dashboard contract checker is not wired into CI.")

    if findings:
        return False, "Monitoring dashboard contract violations: " + "; ".join(findings)
    return True, f"Monitoring dashboard contract is current: {output_path}"


def validate_monitoring_dashboard_definition(repo_root: Path = REPO_ROOT) -> tuple[str, ...]:
    required_files = [
        "backend/src/forgeml/modules/monitoring/domain/entities.py",
        "backend/src/forgeml/modules/monitoring/application/services.py",
        "backend/src/forgeml/modules/monitoring/infrastructure/sqlalchemy_repositories.py",
        "backend/src/forgeml/modules/monitoring/api/routes.py",
        "backend/src/forgeml/modules/monitoring/api/schemas.py",
        "backend/tests/unit/monitoring/test_monitoring_service.py",
        "backend/tests/api/test_monitoring_api.py",
        "frontend/src/modules/monitoring/api/monitoring.ts",
        "frontend/src/modules/monitoring/pages/MonitoringPage.tsx",
        "frontend/src/modules/monitoring/pages/MonitoringPage.test.tsx",
    ]
    findings = [
        f"Missing monitoring dashboard file: {path}"
        for path in required_files
        if not (repo_root / path).is_file()
    ]
    if findings:
        return tuple(findings)

    sources = {
        path: (repo_root / path).read_text(encoding="utf-8") for path in required_files
    }
    contract = serialize_monitoring_dashboard_contract(
        build_monitoring_dashboard_contract()
    )
    required_fragments = (
        (
            "MonitoringOperationsOverview",
            sources["backend/src/forgeml/modules/monitoring/domain/entities.py"],
        ),
        (
            "get_operations_overview",
            sources["backend/src/forgeml/modules/monitoring/application/services.py"],
        ),
        (
            "DriftReportModel",
            sources[
                "backend/src/forgeml/modules/monitoring/infrastructure/sqlalchemy_repositories.py"
            ],
        ),
        (
            "TrainingRunModel",
            sources[
                "backend/src/forgeml/modules/monitoring/infrastructure/sqlalchemy_repositories.py"
            ],
        ),
        (
            "RetrainingRunModel",
            sources[
                "backend/src/forgeml/modules/monitoring/infrastructure/sqlalchemy_repositories.py"
            ],
        ),
        (
            "monitoring/operations",
            sources["backend/src/forgeml/modules/monitoring/api/routes.py"],
        ),
        (
            "MonitoringOperationsOverview",
            sources["frontend/src/modules/monitoring/api/monitoring.ts"],
        ),
        (
            "Latency Percentiles",
            sources["frontend/src/modules/monitoring/pages/MonitoringPage.tsx"],
        ),
        (
            "Inference Errors",
            sources["frontend/src/modules/monitoring/pages/MonitoringPage.tsx"],
        ),
        (
            "Drift Trends",
            sources["frontend/src/modules/monitoring/pages/MonitoringPage.tsx"],
        ),
        (
            "Training Failures",
            sources["frontend/src/modules/monitoring/pages/MonitoringPage.tsx"],
        ),
        (
            "Retraining Activity",
            sources["frontend/src/modules/monitoring/pages/MonitoringPage.tsx"],
        ),
        ("drift_trends", contract),
        ("training_failures", contract),
        ("retraining_activity", contract),
    )
    missing_fragments = sorted(
        fragment for fragment, source in required_fragments if fragment not in source
    )
    if missing_fragments:
        findings.append(f"Missing monitoring dashboard fragments: {missing_fragments}")

    return tuple(findings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify the ForgeML monitoring dashboard contract."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the checked-in monitoring dashboard contract.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate the checked-in monitoring dashboard contract.",
    )
    args = parser.parse_args(argv)

    if args.write:
        write_monitoring_dashboard_contract(args.output)
        print(f"Wrote monitoring dashboard contract: {args.output}")
        return 0

    passed, detail = check_monitoring_dashboard_contract(args.output)
    print(("PASS " if passed else "FAIL ") + detail)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
