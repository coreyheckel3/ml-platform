from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

RELEASE_EVIDENCE_DRILLDOWN_API_CONTRACT_SCHEMA_VERSION = (
    "forgeml.release_evidence_drilldown_api_contract.v1"
)
DEFAULT_OUTPUT_PATH = Path("contracts/ops/release-evidence-drilldown-api.v1.json")
DEFAULT_CI_PATH = Path(".github/workflows/ci.yml")
REPO_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_SOURCE_ASSETS = (
    "backend/src/forgeml/modules/administration/domain/entities.py",
    "backend/src/forgeml/modules/administration/repositories/interfaces.py",
    "backend/src/forgeml/modules/administration/application/services.py",
    "backend/src/forgeml/modules/administration/api/routes.py",
    "backend/src/forgeml/modules/administration/api/schemas.py",
    "backend/src/forgeml/modules/administration/infrastructure/sqlalchemy_models.py",
    "backend/src/forgeml/modules/administration/infrastructure/sqlalchemy_repositories.py",
    "backend/src/forgeml/platform/release_evidence/retrieval.py",
    "backend/alembic/versions/202607190016_release_evidence_reports.py",
    "backend/tests/api/test_administration_api.py",
    "backend/tests/unit/administration/test_administration_service.py",
    "backend/tests/integration/administration/test_audit_log_repository.py",
    "frontend/src/modules/release_evidence/api/releaseEvidence.ts",
    "frontend/src/modules/release_evidence/pages/ReleaseEvidencePage.tsx",
    "frontend/src/modules/release_evidence/pages/ReleaseEvidencePage.test.tsx",
    "frontend/tests/e2e/fixtures/forgemlApiMock.ts",
    "contracts/openapi/forgeml.v1.openapi.json",
    "contracts/security/permission-catalog.v1.json",
    "docs/runbooks/production-readiness.md",
    "docs/portfolio/evidence-map.md",
    "docs/portfolio/reviewer-guide.md",
    "contracts/ops/README.md",
)

REQUIRED_ENDPOINTS = (
    ("GET", "/api/v1/admin/release-evidence/reports"),
    ("GET", "/api/v1/admin/release-evidence/reports/{report_id}"),
    ("POST", "/api/v1/admin/release-evidence/reports/retrieve"),
)

REQUIRED_PERMISSIONS = (
    "admin:release_evidence:read",
    "admin:release_evidence:retrieve",
)

REQUIRED_AUDIT_ACTIONS = (
    "release_evidence.retrieve",
    "release_evidence.retrieve_failed",
)


def build_release_evidence_drilldown_api_contract() -> dict[str, Any]:
    return {
        "schema_version": RELEASE_EVIDENCE_DRILLDOWN_API_CONTRACT_SCHEMA_VERSION,
        "generated_from": [
            "forgeml.modules.administration",
            "forgeml.platform.release_evidence",
            "frontend.modules.release_evidence",
        ],
        "api": {
            "endpoints": [
                {"method": method, "path": path} for method, path in REQUIRED_ENDPOINTS
            ],
            "response_models": [
                "ReleaseEvidenceReportResponse",
                "ReleaseEvidenceReportListResponse",
            ],
        },
        "rbac": {
            "permissions": list(REQUIRED_PERMISSIONS),
            "read_role": "security_auditor",
            "retrieve_role": "platform_admin",
        },
        "persistence": {
            "table": "release_evidence_reports",
            "repository": "ReleaseEvidenceReportRepository",
            "sqlalchemy_repository": "SqlAlchemyReleaseEvidenceReportRepository",
            "head_revision": "202607190016",
        },
        "audit": {"actions": list(REQUIRED_AUDIT_ACTIONS)},
        "ui": {
            "route": "/release-evidence",
            "section": "API Evidence Drilldown",
            "api_client": "frontend/src/modules/release_evidence/api/releaseEvidence.ts",
        },
        "required_source_assets": list(REQUIRED_SOURCE_ASSETS),
        "quality_gates": [
            "python scripts/ci/check_release_evidence_drilldown_api_contract.py",
            "backend/tests/api/test_administration_api.py",
            "backend/tests/unit/administration/test_administration_service.py",
            "backend/tests/integration/administration/test_audit_log_repository.py",
            "frontend/src/modules/release_evidence/pages/ReleaseEvidencePage.test.tsx",
        ],
        "summary": {
            "endpoint_count": len(REQUIRED_ENDPOINTS),
            "permission_count": len(REQUIRED_PERMISSIONS),
            "source_asset_count": len(REQUIRED_SOURCE_ASSETS),
        },
    }


def serialize_release_evidence_drilldown_api_contract(contract: dict[str, Any]) -> str:
    return json.dumps(contract, indent=2, sort_keys=True) + "\n"


def write_release_evidence_drilldown_api_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        serialize_release_evidence_drilldown_api_contract(
            build_release_evidence_drilldown_api_contract()
        ),
        encoding="utf-8",
    )


def check_release_evidence_drilldown_api_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    *,
    ci_path: Path = DEFAULT_CI_PATH,
    repo_root: Path = REPO_ROOT,
) -> tuple[bool, str]:
    findings = list(validate_release_evidence_drilldown_api_definition(repo_root))
    if not output_path.is_file():
        findings.append(f"Release evidence drilldown API contract does not exist: {output_path}")
    else:
        expected = serialize_release_evidence_drilldown_api_contract(
            build_release_evidence_drilldown_api_contract()
        )
        actual = output_path.read_text(encoding="utf-8")
        if actual != expected:
            findings.append(f"Release evidence drilldown API contract is stale: {output_path}")

    if not ci_path.is_file():
        findings.append(f"CI workflow does not exist: {ci_path}")
    else:
        ci_source = ci_path.read_text(encoding="utf-8")
        if "python scripts/ci/check_release_evidence_drilldown_api_contract.py" not in ci_source:
            findings.append("Release evidence drilldown API checker is not wired into CI.")

    if findings:
        return False, "Release evidence drilldown API violations: " + "; ".join(findings)
    return True, f"Release evidence drilldown API contract is current: {output_path}"


def validate_release_evidence_drilldown_api_definition(
    repo_root: Path = REPO_ROOT,
) -> tuple[str, ...]:
    findings: list[str] = []
    contract = build_release_evidence_drilldown_api_contract()

    for source_asset in contract["required_source_assets"]:
        if not (repo_root / source_asset).is_file():
            findings.append(f"Missing release evidence drilldown API asset: {source_asset}")

    service_source = _read(
        repo_root,
        "backend/src/forgeml/modules/administration/application/services.py",
    )
    routes_source = _read(repo_root, "backend/src/forgeml/modules/administration/api/routes.py")
    schemas_source = _read(
        repo_root,
        "backend/src/forgeml/modules/administration/api/schemas.py",
    )
    interfaces_source = _read(
        repo_root,
        "backend/src/forgeml/modules/administration/repositories/interfaces.py",
    )
    models_source = _read(
        repo_root,
        "backend/src/forgeml/modules/administration/infrastructure/sqlalchemy_models.py",
    )
    repositories_source = _read(
        repo_root,
        "backend/src/forgeml/modules/administration/infrastructure/sqlalchemy_repositories.py",
    )
    migration_source = _read(
        repo_root,
        "backend/alembic/versions/202607190016_release_evidence_reports.py",
    )
    permissions_source = _read(repo_root, "backend/src/forgeml/platform/security/permissions.py")
    release_evidence_source = _read(
        repo_root,
        "backend/src/forgeml/platform/release_evidence/retrieval.py",
    )
    openapi_contract = _read_json(repo_root / "contracts/openapi/forgeml.v1.openapi.json")
    permission_contract = _read_json(repo_root / "contracts/security/permission-catalog.v1.json")
    frontend_api_source = _read(
        repo_root,
        "frontend/src/modules/release_evidence/api/releaseEvidence.ts",
    )
    page_source = _read(
        repo_root,
        "frontend/src/modules/release_evidence/pages/ReleaseEvidencePage.tsx",
    )
    page_test_source = _read(
        repo_root,
        "frontend/src/modules/release_evidence/pages/ReleaseEvidencePage.test.tsx",
    )
    e2e_mock_source = _read(repo_root, "frontend/tests/e2e/fixtures/forgemlApiMock.ts")
    production_readiness_source = _read(repo_root, "scripts/ci/production_readiness.py")
    ci_source = _read(repo_root, ".github/workflows/ci.yml")
    manifest_builder_source = _read(repo_root, "scripts/ops/build_release_manifest.py")
    runbook_source = _read(repo_root, "docs/runbooks/production-readiness.md")
    evidence_map_source = _read(repo_root, "docs/portfolio/evidence-map.md")
    reviewer_guide_source = _read(repo_root, "docs/portfolio/reviewer-guide.md")
    ops_readme_source = _read(repo_root, "contracts/ops/README.md")

    _require_fragments(
        findings,
        "administration service",
        service_source,
        (
            "retrieve_release_evidence",
            "ReleaseEvidenceRetrievalConfig",
            "ReleaseEvidenceReportRepository",
            "RELEASE_EVIDENCE_REQUIRED_ARTIFACTS",
            *REQUIRED_AUDIT_ACTIONS,
            *REQUIRED_PERMISSIONS,
        ),
    )
    _require_fragments(
        findings,
        "administration routes",
        routes_source,
        (
            '"/admin/release-evidence/reports"',
            '"/admin/release-evidence/reports/retrieve"',
            '"/admin/release-evidence/reports/{report_id}"',
            "get_release_evidence_report",
            "retrieve_release_evidence_report",
        ),
    )
    _require_fragments(
        findings,
        "administration schemas",
        schemas_source,
        ("ReleaseEvidenceReportResponse", "ReleaseEvidenceReportListResponse"),
    )
    _require_fragments(
        findings,
        "repository interfaces",
        interfaces_source,
        ("ReleaseEvidenceReportRepository", "ReleaseEvidenceReportFilters"),
    )
    _require_fragments(
        findings,
        "SQLAlchemy model",
        models_source,
        (
            "ReleaseEvidenceReportModel",
            "release_evidence_reports",
            "ix_release_evidence_reports_organization_created",
        ),
    )
    _require_fragments(
        findings,
        "SQLAlchemy repository",
        repositories_source,
        ("SqlAlchemyReleaseEvidenceReportRepository", "list_reports", "get_report"),
    )
    _require_fragments(
        findings,
        "Alembic migration",
        migration_source,
        ("202607190016", "release_evidence_reports", "organization_id"),
    )
    _require_fragments(
        findings,
        "release evidence runtime",
        release_evidence_source,
        (
            "RELEASE_EVIDENCE_REQUIRED_ARTIFACTS",
            "RELEASE_EVIDENCE_REQUIRED_QUALITY_GATES",
            "release_evidence_drilldown_api_contract",
        ),
    )
    _require_fragments(findings, "permissions", permissions_source, REQUIRED_PERMISSIONS)
    _require_fragments(
        findings,
        "frontend API client",
        frontend_api_source,
        (
            "listReleaseEvidenceReports",
            "getReleaseEvidenceReport",
            "retrieveReleaseEvidenceReport",
        ),
    )
    _require_fragments(
        findings,
        "release evidence page",
        page_source,
        ("API Evidence Drilldown", "Retrieve evidence", *REQUIRED_AUDIT_ACTIONS),
    )
    _require_fragments(
        findings,
        "release evidence page test",
        page_test_source,
        ("API Evidence Drilldown", "retrieve evidence", "authorization"),
    )
    _require_fragments(
        findings,
        "Playwright API mock",
        e2e_mock_source,
        ("releaseEvidenceReports", "releaseEvidenceReport", *REQUIRED_AUDIT_ACTIONS),
    )
    _require_fragments(
        findings,
        "production readiness",
        production_readiness_source,
        ("check_release_evidence_drilldown_api_contract",),
    )
    _require_fragments(
        findings,
        "CI workflow",
        ci_source,
        ("python scripts/ci/check_release_evidence_drilldown_api_contract.py",),
    )
    _require_fragments(
        findings,
        "release manifest builder",
        manifest_builder_source,
        ("release_evidence_drilldown_api_contract",),
    )
    _require_fragments(
        findings,
        "production readiness runbook",
        runbook_source,
        ("check_release_evidence_drilldown_api_contract.py",),
    )
    _require_fragments(
        findings,
        "portfolio evidence map",
        evidence_map_source,
        ("Release evidence drilldown API",),
    )
    _require_fragments(
        findings,
        "portfolio reviewer guide",
        reviewer_guide_source,
        ("check_release_evidence_drilldown_api_contract.py",),
    )
    _require_fragments(
        findings,
        "operations contracts README",
        ops_readme_source,
        ("release-evidence-drilldown-api.v1.json",),
    )

    if openapi_contract:
        paths = openapi_contract.get("paths", {})
        if isinstance(paths, dict):
            for method, path in REQUIRED_ENDPOINTS:
                operations = paths.get(path)
                if not isinstance(operations, dict) or method.lower() not in operations:
                    findings.append(f"OpenAPI contract is missing {method} {path}.")

    permission_codes = {
        permission.get("code")
        for permission in permission_contract.get("permissions", [])
        if isinstance(permission, dict)
    }
    missing_permissions = sorted(set(REQUIRED_PERMISSIONS) - permission_codes)
    if missing_permissions:
        findings.append(
            f"Permission catalog is missing release evidence permissions: {missing_permissions}"
        )

    return tuple(findings)


def _require_fragments(
    findings: list[str],
    label: str,
    source: str,
    fragments: tuple[str, ...],
) -> None:
    missing = [fragment for fragment in fragments if fragment not in source]
    if missing:
        findings.append(f"{label} is missing fragments: {missing}")


def _read(repo_root: Path, path: str) -> str:
    file_path = repo_root / path
    if not file_path.is_file():
        return ""
    return file_path.read_text(encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify the ForgeML release evidence drilldown API contract."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the checked-in release evidence drilldown API contract.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate the checked-in release evidence drilldown API contract.",
    )
    args = parser.parse_args(argv)

    if args.write:
        write_release_evidence_drilldown_api_contract(args.output)
        return 0

    passed, detail = check_release_evidence_drilldown_api_contract(args.output)
    print(detail)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
