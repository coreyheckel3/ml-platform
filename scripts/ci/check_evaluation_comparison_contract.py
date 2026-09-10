from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

EVALUATION_COMPARISON_CONTRACT_SCHEMA_VERSION = (
    "forgeml.evaluation_comparison_contract.v1"
)
DEFAULT_OUTPUT_PATH = Path("contracts/ops/evaluation-comparison.v1.json")
DEFAULT_CI_PATH = Path(".github/workflows/ci.yml")
REPO_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_SOURCE_ASSETS = (
    "backend/src/forgeml/modules/evaluation/domain/entities.py",
    "backend/src/forgeml/modules/evaluation/repositories/interfaces.py",
    "backend/src/forgeml/modules/evaluation/infrastructure/sqlalchemy_repositories.py",
    "backend/src/forgeml/modules/evaluation/application/services.py",
    "backend/src/forgeml/modules/evaluation/api/routes.py",
    "backend/src/forgeml/modules/evaluation/api/schemas.py",
    "backend/src/forgeml/main.py",
    "backend/src/forgeml/platform/security/permissions.py",
    "backend/tests/unit/evaluation/test_evaluation_service.py",
    "backend/tests/integration/evaluation/test_evaluation_repository.py",
    "backend/tests/api/test_evaluation_api.py",
    "backend/tests/unit/ops/test_evaluation_comparison_contract.py",
    "frontend/src/modules/evaluation/api/evaluation.ts",
    "frontend/src/modules/evaluation/pages/EvaluationPage.tsx",
    "frontend/src/modules/evaluation/pages/EvaluationPage.test.tsx",
    "frontend/src/app/navigation.ts",
    "frontend/src/app/routes.tsx",
    "frontend/src/app/App.test.tsx",
    "frontend/tests/e2e/fixtures/forgemlApiMock.ts",
    "frontend/tests/e2e/smoke.spec.ts",
    "frontend/tests/e2e/demo-walkthrough.spec.ts",
    "frontend/tests/e2e/demo-screenshots.spec.ts",
    "frontend/src/modules/release_evidence/data/releaseEvidence.ts",
    "docs/runbooks/evaluation-comparison.md",
    "docs/runbooks/demo-readiness.md",
    "docs/runbooks/production-readiness.md",
    "docs/portfolio/evidence-map.md",
    "docs/portfolio/screenshot-catalog.md",
    "Makefile",
)


def build_evaluation_comparison_contract() -> dict[str, Any]:
    return {
        "schema_version": EVALUATION_COMPARISON_CONTRACT_SCHEMA_VERSION,
        "generated_from": [
            "backend.modules.evaluation",
            "backend.platform.security.permissions",
            "frontend.modules.evaluation",
            "frontend.tests.e2e.forgeml_api_mock",
            "docs.runbooks.evaluation-comparison",
        ],
        "route": {
            "path": "/evaluation",
            "label": "Evaluation",
            "navigation_icon": "Scale",
        },
        "api_surface": [
            "GET /api/v1/projects/{project_id}/evaluation/comparison",
        ],
        "rbac_permission": "evaluation:read",
        "schema_versions": [
            "forgeml.evaluation_comparison.v1",
            EVALUATION_COMPARISON_CONTRACT_SCHEMA_VERSION,
        ],
        "required_source_assets": list(REQUIRED_SOURCE_ASSETS),
        "required_backend_layers": [
            "domain_entities",
            "repository_interface",
            "sqlalchemy_repository",
            "application_service",
            "api_route",
            "pydantic_schemas",
            "unit_tests",
            "integration_tests",
            "api_tests",
        ],
        "required_ui_sections": [
            "Run Leaderboard",
            "Metric Slices",
            "Model Card Evidence",
            "Approval Checklist",
            "Evaluation Narrative",
        ],
        "required_comparison_signals": [
            "primary_metric_name",
            "delta_from_baseline",
            "quality_score",
            "metric_summary",
            "signature_summary",
            "lineage_summary",
            "risk_flags",
            "approval_checklist",
        ],
        "required_release_signals": [
            "evaluation_comparison_contract",
            "contracts/ops/evaluation-comparison.v1.json",
            "14-evaluation.png",
            "evaluation:read",
        ],
        "operator_commands": [
            "make evaluation-comparison",
            "PYTHONPATH=. python scripts/ci/check_evaluation_comparison_contract.py",
            "PYTHONPATH=backend/src:. python scripts/ci/generate_openapi_contract.py --check",
            "PYTHONPATH=. python scripts/ci/check_permission_catalog.py",
        ],
        "quality_gates": [
            "python scripts/ci/check_evaluation_comparison_contract.py",
            "backend/tests/unit/evaluation/test_evaluation_service.py",
            "backend/tests/integration/evaluation/test_evaluation_repository.py",
            "backend/tests/api/test_evaluation_api.py",
            "frontend/src/modules/evaluation/pages/EvaluationPage.test.tsx",
            "frontend/tests/e2e/demo-walkthrough.spec.ts",
            "frontend/tests/e2e/demo-screenshots.spec.ts",
        ],
        "summary": {
            "source_asset_count": len(REQUIRED_SOURCE_ASSETS),
            "backend_layer_count": 9,
            "ui_section_count": 5,
            "comparison_signal_count": 8,
            "release_signal_count": 4,
        },
    }


def serialize_evaluation_comparison_contract(contract: dict[str, Any]) -> str:
    return json.dumps(contract, indent=2, sort_keys=True) + "\n"


def write_evaluation_comparison_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        serialize_evaluation_comparison_contract(
            build_evaluation_comparison_contract()
        ),
        encoding="utf-8",
    )


def check_evaluation_comparison_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    *,
    ci_path: Path = DEFAULT_CI_PATH,
    repo_root: Path = REPO_ROOT,
) -> tuple[bool, str]:
    findings = list(validate_evaluation_comparison_definition(repo_root))
    if not output_path.is_file():
        findings.append(f"Evaluation comparison contract does not exist: {output_path}")
    else:
        expected = serialize_evaluation_comparison_contract(
            build_evaluation_comparison_contract()
        )
        actual = output_path.read_text(encoding="utf-8")
        if actual != expected:
            findings.append(f"Evaluation comparison contract is stale: {output_path}")

    if not ci_path.is_file():
        findings.append(f"CI workflow does not exist: {ci_path}")
    else:
        ci_source = ci_path.read_text(encoding="utf-8")
        if "python scripts/ci/check_evaluation_comparison_contract.py" not in ci_source:
            findings.append("Evaluation comparison contract checker is not wired into CI.")

    if findings:
        return False, "Evaluation comparison violations: " + "; ".join(findings)
    return True, f"Evaluation comparison contract is current: {output_path}"


def validate_evaluation_comparison_definition(
    repo_root: Path = REPO_ROOT,
) -> tuple[str, ...]:
    findings: list[str] = []
    contract = build_evaluation_comparison_contract()

    for source_asset in contract["required_source_assets"]:
        if not (repo_root / source_asset).is_file():
            findings.append(f"Missing evaluation comparison source asset: {source_asset}")

    domain_source = _read(
        repo_root, "backend/src/forgeml/modules/evaluation/domain/entities.py"
    )
    interface_source = _read(
        repo_root, "backend/src/forgeml/modules/evaluation/repositories/interfaces.py"
    )
    repository_source = _read(
        repo_root,
        "backend/src/forgeml/modules/evaluation/infrastructure/"
        "sqlalchemy_repositories.py",
    )
    service_source = _read(
        repo_root, "backend/src/forgeml/modules/evaluation/application/services.py"
    )
    route_source = _read(repo_root, "backend/src/forgeml/modules/evaluation/api/routes.py")
    schema_source = _read(
        repo_root, "backend/src/forgeml/modules/evaluation/api/schemas.py"
    )
    main_source = _read(repo_root, "backend/src/forgeml/main.py")
    permissions_source = _read(repo_root, "backend/src/forgeml/platform/security/permissions.py")
    frontend_api_source = _read(repo_root, "frontend/src/modules/evaluation/api/evaluation.ts")
    frontend_page_source = _read(
        repo_root, "frontend/src/modules/evaluation/pages/EvaluationPage.tsx"
    )
    frontend_test_source = _read(
        repo_root, "frontend/src/modules/evaluation/pages/EvaluationPage.test.tsx"
    )
    routes_source = _read(repo_root, "frontend/src/app/routes.tsx")
    navigation_source = _read(repo_root, "frontend/src/app/navigation.ts")
    app_test_source = _read(repo_root, "frontend/src/app/App.test.tsx")
    mock_source = _read(repo_root, "frontend/tests/e2e/fixtures/forgemlApiMock.ts")
    smoke_source = _read(repo_root, "frontend/tests/e2e/smoke.spec.ts")
    walkthrough_source = _read(repo_root, "frontend/tests/e2e/demo-walkthrough.spec.ts")
    screenshots_source = _read(repo_root, "frontend/tests/e2e/demo-screenshots.spec.ts")
    release_data_source = _read(
        repo_root, "frontend/src/modules/release_evidence/data/releaseEvidence.ts"
    )
    runbook_source = _read(repo_root, "docs/runbooks/evaluation-comparison.md")
    demo_runbook_source = _read(repo_root, "docs/runbooks/demo-readiness.md")
    production_runbook_source = _read(repo_root, "docs/runbooks/production-readiness.md")
    evidence_map_source = _read(repo_root, "docs/portfolio/evidence-map.md")
    screenshot_catalog_source = _read(repo_root, "docs/portfolio/screenshot-catalog.md")
    makefile_source = _read(repo_root, "Makefile")

    _require_fragments(
        findings,
        "evaluation domain",
        domain_source,
        (
            "EVALUATION_COMPARISON_SCHEMA_VERSION",
            "EvaluationCandidate",
            "EvaluationModelEvidence",
            "EvaluationMetricSlice",
            "EvaluationApprovalChecklistItem",
            "EvaluationComparisonSummary",
        ),
    )
    _require_fragments(
        findings,
        "evaluation repository boundary",
        interface_source + repository_source,
        (
            "EvaluationComparisonRepository",
            "load_snapshot",
            "SqlAlchemyEvaluationComparisonRepository",
            "ProjectModel.organization_id",
            "ExperimentRunModel",
            "TrainingRunModel",
            "ModelVersionModel",
            "ModelApprovalModel",
            "ModelLineageModel",
        ),
    )
    _require_fragments(
        findings,
        "evaluation service",
        service_source,
        (
            "GetEvaluationComparisonQuery",
            "get_evaluation_comparison_summary",
            "evaluation:read",
            "_select_primary_metric",
            "_build_metric_slices",
            "_build_approval_checklist",
            "_build_narrative",
        ),
    )
    _require_fragments(
        findings,
        "evaluation api",
        route_source + schema_source + main_source,
        (
            "/projects/{project_id}/evaluation/comparison",
            "EvaluationComparisonSummaryResponse",
            "get_current_principal",
            "evaluation_router",
            "include_router(evaluation_router",
        ),
    )
    _require_fragments(
        findings,
        "evaluation permission catalog",
        permissions_source,
        (
            "evaluation:read",
            "Read experiment evaluation comparisons, metric slices, and model card evidence.",
            "ml_engineer",
            "ml_operator",
            "ml_viewer",
        ),
    )
    _require_fragments(
        findings,
        "evaluation frontend",
        frontend_api_source + frontend_page_source + frontend_test_source,
        (
            "getEvaluationComparisonSummary",
            "/api/v1/projects/${projectId}/evaluation/comparison",
            "Run Leaderboard",
            "Metric Slices",
            "Model Card Evidence",
            "Approval Checklist",
            "Evaluation Narrative",
            "refetchInterval",
        ),
    )
    _require_fragments(
        findings,
        "evaluation route and navigation",
        routes_source + navigation_source + app_test_source,
        (
            "loadEvaluationPage",
            "/evaluation",
            "Evaluation",
            "Scale",
        ),
    )
    _require_fragments(
        findings,
        "evaluation e2e mock and tests",
        mock_source + smoke_source + walkthrough_source + screenshots_source,
        (
            "buildEvaluationComparisonSummary",
            "Run Leaderboard",
            "Metric Slices",
            "Model Card Evidence",
            "14-evaluation.png",
        ),
    )
    _require_fragments(
        findings,
        "evaluation release evidence",
        release_data_source,
        (
            "Evaluation Comparison Contract",
            "evaluation_comparison_contract",
            "contracts/ops/evaluation-comparison.v1.json",
            "14-evaluation.png",
        ),
    )
    _require_fragments(
        findings,
        "evaluation docs",
        (
            runbook_source
            + demo_runbook_source
            + production_runbook_source
            + evidence_map_source
            + screenshot_catalog_source
        ),
        (
            "Sprint 75",
            "Evaluation",
            "contracts/ops/evaluation-comparison.v1.json",
            "14-evaluation.png",
            "make evaluation-comparison",
        ),
    )
    _require_fragments(
        findings,
        "evaluation make target",
        makefile_source,
        (
            "evaluation-comparison",
            "scripts/ci/check_evaluation_comparison_contract.py",
        ),
    )

    return tuple(findings)


def _require_fragments(
    findings: list[str],
    label: str,
    source: str,
    fragments: tuple[str, ...],
) -> None:
    missing_fragments = sorted(fragment for fragment in fragments if fragment not in source)
    if missing_fragments:
        findings.append(f"{label} is missing fragments: {missing_fragments}")


def _read(repo_root: Path, relative_path: str) -> str:
    path = repo_root / relative_path
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify the ForgeML evaluation comparison contract."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the checked-in evaluation comparison contract.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate the checked-in evaluation comparison contract.",
    )
    args = parser.parse_args(argv)

    if args.write:
        write_evaluation_comparison_contract(args.output)
        print(f"Wrote evaluation comparison contract: {args.output}")
        return 0

    passed, detail = check_evaluation_comparison_contract(args.output)
    print(("PASS " if passed else "FAIL ") + detail)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
