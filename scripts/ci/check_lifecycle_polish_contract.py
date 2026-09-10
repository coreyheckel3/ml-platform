from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

LIFECYCLE_POLISH_CONTRACT_SCHEMA_VERSION = "forgeml.lifecycle_polish_contract.v1"
DEFAULT_OUTPUT_PATH = Path("contracts/ops/lifecycle-polish.v1.json")
DEFAULT_CI_PATH = Path(".github/workflows/ci.yml")
REPO_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_SOURCE_ASSETS = (
    "backend/src/forgeml/modules/lifecycle/domain/entities.py",
    "backend/src/forgeml/modules/lifecycle/repositories/interfaces.py",
    "backend/src/forgeml/modules/lifecycle/infrastructure/sqlalchemy_repositories.py",
    "backend/src/forgeml/modules/lifecycle/application/services.py",
    "backend/src/forgeml/modules/lifecycle/api/routes.py",
    "backend/src/forgeml/modules/lifecycle/api/schemas.py",
    "backend/src/forgeml/main.py",
    "backend/src/forgeml/platform/security/permissions.py",
    "backend/tests/unit/lifecycle/test_lifecycle_service.py",
    "backend/tests/integration/lifecycle/test_lifecycle_repository.py",
    "backend/tests/api/test_lifecycle_api.py",
    "frontend/src/modules/lifecycle/api/lifecycle.ts",
    "frontend/src/modules/lifecycle/pages/LifecyclePage.tsx",
    "frontend/src/modules/lifecycle/pages/LifecyclePage.test.tsx",
    "frontend/src/app/navigation.ts",
    "frontend/src/app/routes.tsx",
    "frontend/src/app/App.test.tsx",
    "frontend/tests/e2e/fixtures/forgemlApiMock.ts",
    "frontend/tests/e2e/smoke.spec.ts",
    "frontend/tests/e2e/demo-walkthrough.spec.ts",
    "frontend/tests/e2e/demo-screenshots.spec.ts",
    "frontend/src/modules/release_evidence/data/releaseEvidence.ts",
    "docs/runbooks/lifecycle-polish.md",
    "docs/runbooks/demo-readiness.md",
    "docs/runbooks/production-readiness.md",
    "docs/portfolio/evidence-map.md",
    "docs/portfolio/screenshot-catalog.md",
    "Makefile",
)


def build_lifecycle_polish_contract() -> dict[str, Any]:
    return {
        "schema_version": LIFECYCLE_POLISH_CONTRACT_SCHEMA_VERSION,
        "generated_from": [
            "backend.modules.lifecycle",
            "backend.platform.security.permissions",
            "frontend.modules.lifecycle",
            "frontend.tests.e2e.forgeml_api_mock",
            "docs.runbooks.lifecycle-polish",
        ],
        "route": {
            "path": "/lifecycle",
            "label": "Lifecycle",
            "navigation_icon": "GitPullRequestArrow",
        },
        "api_surface": [
            "GET /api/v1/projects/{project_id}/lifecycle/summary",
        ],
        "rbac_permission": "lifecycle:read",
        "schema_versions": [
            "forgeml.project_lifecycle.v1",
            LIFECYCLE_POLISH_CONTRACT_SCHEMA_VERSION,
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
            "End-to-End Lifecycle Readiness",
            "Stage Readiness",
            "Recommended Actions",
            "Project Signals",
            "Dependency Map",
        ],
        "required_lifecycle_stages": [
            "datasets",
            "feature_store",
            "experiments",
            "training",
            "model_registry",
            "deployment",
            "inference",
            "monitoring",
            "drift_detection",
            "retraining",
        ],
        "required_release_signals": [
            "lifecycle_polish_contract",
            "contracts/ops/lifecycle-polish.v1.json",
            "13-lifecycle.png",
            "lifecycle:read",
        ],
        "operator_commands": [
            "make lifecycle-polish",
            "PYTHONPATH=. python scripts/ci/check_lifecycle_polish_contract.py",
            "PYTHONPATH=backend/src:. python scripts/ci/generate_openapi_contract.py --check",
            "PYTHONPATH=. python scripts/ci/check_permission_catalog.py",
        ],
        "quality_gates": [
            "python scripts/ci/check_lifecycle_polish_contract.py",
            "backend/tests/unit/lifecycle/test_lifecycle_service.py",
            "backend/tests/integration/lifecycle/test_lifecycle_repository.py",
            "backend/tests/api/test_lifecycle_api.py",
            "frontend/src/modules/lifecycle/pages/LifecyclePage.test.tsx",
            "frontend/tests/e2e/demo-walkthrough.spec.ts",
            "frontend/tests/e2e/demo-screenshots.spec.ts",
        ],
        "summary": {
            "source_asset_count": len(REQUIRED_SOURCE_ASSETS),
            "backend_layer_count": 9,
            "ui_section_count": 5,
            "lifecycle_stage_count": 10,
            "release_signal_count": 4,
        },
    }


def serialize_lifecycle_polish_contract(contract: dict[str, Any]) -> str:
    return json.dumps(contract, indent=2, sort_keys=True) + "\n"


def write_lifecycle_polish_contract(output_path: Path = DEFAULT_OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        serialize_lifecycle_polish_contract(build_lifecycle_polish_contract()),
        encoding="utf-8",
    )


def check_lifecycle_polish_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    *,
    ci_path: Path = DEFAULT_CI_PATH,
    repo_root: Path = REPO_ROOT,
) -> tuple[bool, str]:
    findings = list(validate_lifecycle_polish_definition(repo_root))
    if not output_path.is_file():
        findings.append(f"Lifecycle polish contract does not exist: {output_path}")
    else:
        expected = serialize_lifecycle_polish_contract(
            build_lifecycle_polish_contract()
        )
        actual = output_path.read_text(encoding="utf-8")
        if actual != expected:
            findings.append(f"Lifecycle polish contract is stale: {output_path}")

    if not ci_path.is_file():
        findings.append(f"CI workflow does not exist: {ci_path}")
    else:
        ci_source = ci_path.read_text(encoding="utf-8")
        if "python scripts/ci/check_lifecycle_polish_contract.py" not in ci_source:
            findings.append("Lifecycle polish contract checker is not wired into CI.")

    if findings:
        return False, "Lifecycle polish violations: " + "; ".join(findings)
    return True, f"Lifecycle polish contract is current: {output_path}"


def validate_lifecycle_polish_definition(
    repo_root: Path = REPO_ROOT,
) -> tuple[str, ...]:
    findings: list[str] = []
    contract = build_lifecycle_polish_contract()

    for source_asset in contract["required_source_assets"]:
        if not (repo_root / source_asset).is_file():
            findings.append(f"Missing lifecycle polish source asset: {source_asset}")

    domain_source = _read(
        repo_root, "backend/src/forgeml/modules/lifecycle/domain/entities.py"
    )
    repository_source = _read(
        repo_root,
        "backend/src/forgeml/modules/lifecycle/infrastructure/sqlalchemy_repositories.py",
    )
    interface_source = _read(
        repo_root,
        "backend/src/forgeml/modules/lifecycle/repositories/interfaces.py",
    )
    service_source = _read(
        repo_root, "backend/src/forgeml/modules/lifecycle/application/services.py"
    )
    route_source = _read(repo_root, "backend/src/forgeml/modules/lifecycle/api/routes.py")
    schema_source = _read(
        repo_root, "backend/src/forgeml/modules/lifecycle/api/schemas.py"
    )
    main_source = _read(repo_root, "backend/src/forgeml/main.py")
    permissions_source = _read(repo_root, "backend/src/forgeml/platform/security/permissions.py")
    frontend_api_source = _read(repo_root, "frontend/src/modules/lifecycle/api/lifecycle.ts")
    frontend_page_source = _read(
        repo_root, "frontend/src/modules/lifecycle/pages/LifecyclePage.tsx"
    )
    frontend_test_source = _read(
        repo_root, "frontend/src/modules/lifecycle/pages/LifecyclePage.test.tsx"
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
    lifecycle_runbook_source = _read(repo_root, "docs/runbooks/lifecycle-polish.md")
    demo_runbook_source = _read(repo_root, "docs/runbooks/demo-readiness.md")
    production_runbook_source = _read(repo_root, "docs/runbooks/production-readiness.md")
    evidence_map_source = _read(repo_root, "docs/portfolio/evidence-map.md")
    screenshot_catalog_source = _read(repo_root, "docs/portfolio/screenshot-catalog.md")
    makefile_source = _read(repo_root, "Makefile")

    _require_fragments(
        findings,
        "lifecycle domain",
        domain_source,
        (
            "LIFECYCLE_SCHEMA_VERSION",
            "ProjectLifecycleSnapshot",
            "ProjectLifecycleStage",
            "ProjectLifecycleDependency",
            "ProjectLifecycleSummary",
        ),
    )
    _require_fragments(
        findings,
        "lifecycle repository boundary",
        interface_source + repository_source,
        (
            "ProjectLifecycleRepository",
            "load_snapshot",
            "SqlAlchemyProjectLifecycleRepository",
            "ProjectModel.organization_id",
            "DatasetVersionModel.dataset_id",
            "TrainingRunModel.organization_id",
            "RegisteredModelModel.organization_id",
            "InferenceMetricSnapshotModel",
            "RetrainingRunModel.organization_id",
        ),
    )
    _require_fragments(
        findings,
        "lifecycle service",
        service_source,
        (
            "GetProjectLifecycleSummaryQuery",
            "get_project_lifecycle_summary",
            "lifecycle:read",
            "ResourceNotFoundError",
            "readiness_score",
            "recommended_actions",
        ),
    )
    _require_fragments(
        findings,
        "lifecycle api",
        route_source + schema_source + main_source,
        (
            "/projects/{project_id}/lifecycle/summary",
            "ProjectLifecycleSummaryResponse",
            "get_current_principal",
            "lifecycle_router",
            "include_router(lifecycle_router",
        ),
    )
    _require_fragments(
        findings,
        "lifecycle permission catalog",
        permissions_source,
        (
            "lifecycle:read",
            "Read cross-module project lifecycle readiness summaries.",
            "ml_engineer",
            "ml_operator",
            "ml_viewer",
        ),
    )
    _require_fragments(
        findings,
        "lifecycle frontend",
        frontend_api_source + frontend_page_source + frontend_test_source,
        (
            "getProjectLifecycleSummary",
            "/api/v1/projects/${projectId}/lifecycle/summary",
            "End-to-End Lifecycle Readiness",
            "Stage Readiness",
            "Recommended Actions",
            "Project Signals",
            "Dependency Map",
            "refetchInterval",
        ),
    )
    _require_fragments(
        findings,
        "lifecycle route and navigation",
        routes_source + navigation_source + app_test_source,
        (
            "loadLifecyclePage",
            "/lifecycle",
            "Lifecycle",
            "GitPullRequestArrow",
        ),
    )
    _require_fragments(
        findings,
        "lifecycle e2e mock and tests",
        mock_source + smoke_source + walkthrough_source + screenshots_source,
        (
            "buildProjectLifecycleSummary",
            "Stage Readiness",
            "Dependency Map",
            "Project Signals",
            "13-lifecycle.png",
        ),
    )
    _require_fragments(
        findings,
        "lifecycle release evidence",
        release_data_source,
        (
            "Lifecycle Polish Contract",
            "lifecycle_polish_contract",
            "contracts/ops/lifecycle-polish.v1.json",
            "13-lifecycle.png",
        ),
    )
    _require_fragments(
        findings,
        "lifecycle docs",
        lifecycle_runbook_source
        + demo_runbook_source
        + production_runbook_source
        + evidence_map_source
        + screenshot_catalog_source,
        (
            "Sprint 74",
            "Lifecycle",
            "contracts/ops/lifecycle-polish.v1.json",
            "13-lifecycle.png",
            "make lifecycle-polish",
        ),
    )
    _require_fragments(
        findings,
        "lifecycle make target",
        makefile_source,
        (
            "lifecycle-polish",
            "scripts/ci/check_lifecycle_polish_contract.py",
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
        description="Verify the ForgeML project lifecycle polish contract."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the checked-in lifecycle polish contract.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate the checked-in lifecycle polish contract.",
    )
    args = parser.parse_args(argv)

    if args.write:
        write_lifecycle_polish_contract(args.output)
        print(f"Wrote lifecycle polish contract: {args.output}")
        return 0

    passed, detail = check_lifecycle_polish_contract(args.output)
    print(("PASS " if passed else "FAIL ") + detail)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
