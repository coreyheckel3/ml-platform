from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PLATFORM_ADMIN_CONTROLS_CONTRACT_SCHEMA_VERSION = (
    "forgeml.platform_admin_controls_contract.v1"
)
DEFAULT_OUTPUT_PATH = Path("contracts/ops/platform-admin-controls.v1.json")
DEFAULT_CI_PATH = Path(".github/workflows/ci.yml")
REPO_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_SOURCE_ASSETS = (
    "backend/src/forgeml/modules/administration/domain/entities.py",
    "backend/src/forgeml/modules/administration/repositories/interfaces.py",
    "backend/src/forgeml/modules/administration/infrastructure/sqlalchemy_repositories.py",
    "backend/src/forgeml/modules/administration/application/services.py",
    "backend/src/forgeml/modules/administration/api/routes.py",
    "backend/src/forgeml/modules/administration/api/schemas.py",
    "backend/src/forgeml/platform/security/permissions.py",
    "backend/tests/unit/administration/test_administration_service.py",
    "backend/tests/api/test_administration_api.py",
    "backend/tests/integration/administration/test_admin_controls_repository.py",
    "frontend/src/modules/admin_controls/api/adminControls.ts",
    "frontend/src/modules/admin_controls/pages/AdminControlsPage.tsx",
    "frontend/src/modules/admin_controls/pages/AdminControlsPage.test.tsx",
    "frontend/src/app/navigation.ts",
    "frontend/src/app/routes.tsx",
    "frontend/src/app/App.test.tsx",
    "frontend/tests/e2e/fixtures/forgemlApiMock.ts",
    "frontend/tests/e2e/smoke.spec.ts",
    "frontend/tests/e2e/demo-walkthrough.spec.ts",
    "frontend/tests/e2e/demo-screenshots.spec.ts",
    "frontend/src/modules/release_evidence/data/releaseEvidence.ts",
    "frontend/src/modules/release_evidence/pages/ReleaseEvidencePage.test.tsx",
    "docs/runbooks/admin-controls.md",
    "docs/runbooks/production-readiness.md",
    "docs/runbooks/demo-readiness.md",
    "docs/portfolio/evidence-map.md",
    "docs/portfolio/screenshot-catalog.md",
    "Makefile",
)


def build_platform_admin_controls_contract() -> dict[str, Any]:
    return {
        "schema_version": PLATFORM_ADMIN_CONTROLS_CONTRACT_SCHEMA_VERSION,
        "generated_from": [
            "backend.modules.administration",
            "backend.platform.security.permissions",
            "frontend.modules.admin_controls",
            "frontend.tests.e2e.forgeml_api_mock",
            "docs.runbooks.admin-controls",
        ],
        "route": {
            "path": "/admin",
            "label": "Admin",
            "navigation_icon": "ShieldCheck",
        },
        "api_surface": ["GET /api/v1/admin/controls"],
        "rbac_permission": "admin:controls:read",
        "schema_versions": [
            "forgeml.platform_admin_controls.v1",
            PLATFORM_ADMIN_CONTROLS_CONTRACT_SCHEMA_VERSION,
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
            "Organization Overview",
            "User Access",
            "RBAC Matrix",
            "Permission Catalog",
            "Environment Visibility",
            "Safe Admin Workflows",
        ],
        "required_runtime_signals": [
            "production_like",
            "rate_limit_enabled",
            "request_logging_enabled",
            "structured_logging_enabled",
            "readiness_checks_enabled",
            "object_storage_configured",
            "redis_configured",
            "mlflow_tracking_configured",
            "airflow_orchestration_enabled",
            "external_training_profiles_enabled",
            "release_evidence_provider",
        ],
        "required_safeguards": [
            "Tenant isolation",
            "RBAC mutations",
            "Release governance",
            "Runtime guardrails",
        ],
        "required_release_signals": [
            "platform_admin_controls_contract",
            "contracts/ops/platform-admin-controls.v1.json",
            "12-admin-controls.png",
            "admin:controls:read",
        ],
        "operator_commands": [
            "make admin-controls",
            "PYTHONPATH=. python scripts/ci/check_platform_admin_controls_contract.py",
            "PYTHONPATH=. python scripts/ci/check_permission_catalog.py",
            "make production-readiness",
        ],
        "quality_gates": [
            "python scripts/ci/check_platform_admin_controls_contract.py",
            "backend/tests/unit/ops/test_platform_admin_controls_contract.py",
            "backend/tests/unit/administration/test_administration_service.py",
            "backend/tests/integration/administration/test_admin_controls_repository.py",
            "backend/tests/api/test_administration_api.py",
            "frontend/src/modules/admin_controls/pages/AdminControlsPage.test.tsx",
            "frontend/tests/e2e/demo-walkthrough.spec.ts",
            "frontend/tests/e2e/demo-screenshots.spec.ts",
        ],
        "summary": {
            "source_asset_count": len(REQUIRED_SOURCE_ASSETS),
            "backend_layer_count": 9,
            "ui_section_count": 6,
            "runtime_signal_count": 11,
            "safeguard_count": 4,
        },
    }


def serialize_platform_admin_controls_contract(contract: dict[str, Any]) -> str:
    return json.dumps(contract, indent=2, sort_keys=True) + "\n"


def write_platform_admin_controls_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        serialize_platform_admin_controls_contract(
            build_platform_admin_controls_contract()
        ),
        encoding="utf-8",
    )


def check_platform_admin_controls_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    *,
    ci_path: Path = DEFAULT_CI_PATH,
    repo_root: Path = REPO_ROOT,
) -> tuple[bool, str]:
    findings = list(validate_platform_admin_controls_definition(repo_root))
    if not output_path.is_file():
        findings.append(f"Platform admin controls contract does not exist: {output_path}")
    else:
        expected = serialize_platform_admin_controls_contract(
            build_platform_admin_controls_contract()
        )
        actual = output_path.read_text(encoding="utf-8")
        if actual != expected:
            findings.append(f"Platform admin controls contract is stale: {output_path}")

    if not ci_path.is_file():
        findings.append(f"CI workflow does not exist: {ci_path}")
    else:
        ci_source = ci_path.read_text(encoding="utf-8")
        if "python scripts/ci/check_platform_admin_controls_contract.py" not in ci_source:
            findings.append("Platform admin controls contract checker is not wired into CI.")

    if findings:
        return False, "Platform admin controls violations: " + "; ".join(findings)
    return True, f"Platform admin controls contract is current: {output_path}"


def validate_platform_admin_controls_definition(
    repo_root: Path = REPO_ROOT,
) -> tuple[str, ...]:
    findings: list[str] = []
    contract = build_platform_admin_controls_contract()

    for source_asset in contract["required_source_assets"]:
        if not (repo_root / source_asset).is_file():
            findings.append(f"Missing platform admin controls source asset: {source_asset}")

    domain_source = _read(
        repo_root, "backend/src/forgeml/modules/administration/domain/entities.py"
    )
    repository_interface_source = _read(
        repo_root, "backend/src/forgeml/modules/administration/repositories/interfaces.py"
    )
    sqlalchemy_repository_source = _read(
        repo_root,
        "backend/src/forgeml/modules/administration/infrastructure/sqlalchemy_repositories.py",
    )
    service_source = _read(
        repo_root, "backend/src/forgeml/modules/administration/application/services.py"
    )
    route_source = _read(
        repo_root, "backend/src/forgeml/modules/administration/api/routes.py"
    )
    schema_source = _read(
        repo_root, "backend/src/forgeml/modules/administration/api/schemas.py"
    )
    permissions_source = _read(repo_root, "backend/src/forgeml/platform/security/permissions.py")
    frontend_api_source = _read(
        repo_root, "frontend/src/modules/admin_controls/api/adminControls.ts"
    )
    frontend_page_source = _read(
        repo_root, "frontend/src/modules/admin_controls/pages/AdminControlsPage.tsx"
    )
    frontend_test_source = _read(
        repo_root, "frontend/src/modules/admin_controls/pages/AdminControlsPage.test.tsx"
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
    release_test_source = _read(
        repo_root, "frontend/src/modules/release_evidence/pages/ReleaseEvidencePage.test.tsx"
    )
    admin_runbook_source = _read(repo_root, "docs/runbooks/admin-controls.md")
    production_runbook_source = _read(repo_root, "docs/runbooks/production-readiness.md")
    demo_runbook_source = _read(repo_root, "docs/runbooks/demo-readiness.md")
    evidence_map_source = _read(repo_root, "docs/portfolio/evidence-map.md")
    screenshot_catalog_source = _read(repo_root, "docs/portfolio/screenshot-catalog.md")
    makefile_source = _read(repo_root, "Makefile")

    missing_domain_fragments = [
        fragment
        for fragment in (
            "PLATFORM_ADMIN_CONTROLS_SCHEMA_VERSION",
            "AdminOrganizationProfile",
            "AdminUserAccessProfile",
            "AdminControlPlaneSnapshot",
            "AdminEnvironmentSummary",
            "PlatformAdminControls",
        )
        if fragment not in domain_source
    ]
    if missing_domain_fragments:
        findings.append(f"Admin domain read model is missing: {missing_domain_fragments}")

    missing_repository_fragments = [
        fragment
        for fragment in (
            "AdminControlPlaneRepository",
            "load_snapshot",
            "SqlAlchemyAdminControlPlaneRepository",
            "ProjectModel.organization_id",
            "ReleaseEvidenceReportModel.organization_id",
            "UserModel.organization_id",
        )
        if fragment not in repository_interface_source + sqlalchemy_repository_source
    ]
    if missing_repository_fragments:
        findings.append(
            f"Admin repository boundary is missing: {missing_repository_fragments}"
        )

    missing_service_fragments = [
        fragment
        for fragment in (
            "get_platform_admin_controls",
            "GetPlatformAdminControlsQuery",
            "AdminControlsRuntimeConfig",
            "admin:controls:read",
            "ROLE_PRESETS",
            "PERMISSIONS",
            "Tenant isolation",
            "RBAC mutations",
            "Release governance",
            "Runtime guardrails",
            "check_platform_admin_controls_contract.py",
        )
        if fragment not in service_source
    ]
    if missing_service_fragments:
        findings.append(f"Admin service is missing: {missing_service_fragments}")

    missing_api_fragments = [
        fragment
        for fragment in (
            '"/admin/controls"',
            "PlatformAdminControlsResponse",
            "SqlAlchemyAdminControlPlaneRepository",
            "_admin_controls_runtime_config_from_settings",
            "AdminEnvironmentResponse",
        )
        if fragment not in route_source + schema_source
    ]
    if missing_api_fragments:
        findings.append(f"Admin API is missing: {missing_api_fragments}")

    if "admin:controls:read" not in permissions_source:
        findings.append("Permission catalog source does not define admin:controls:read.")
    if "security_auditor" not in permissions_source:
        findings.append("Security auditor role is not visible in permission source.")

    missing_frontend_fragments = [
        fragment
        for fragment in (
            "getPlatformAdminControls",
            "/api/v1/admin/controls",
            "AdminControlsPage",
            *contract["required_ui_sections"],
            "subscribeToSessionChanges",
            "forgeml.platform_admin_controls.v1",
        )
        if fragment not in frontend_api_source + frontend_page_source + frontend_test_source
    ]
    if missing_frontend_fragments:
        findings.append(f"Admin frontend is missing: {missing_frontend_fragments}")

    missing_route_fragments = [
        fragment
        for fragment in ('path: "/admin"', "loadAdminControlsPage", "AdminControlsPage")
        if fragment not in routes_source
    ]
    if missing_route_fragments:
        findings.append(f"Admin route is missing: {missing_route_fragments}")

    missing_navigation_fragments = [
        fragment
        for fragment in ('label: "Admin"', 'path: "/admin"', "ShieldCheck")
        if fragment not in navigation_source
    ]
    if missing_navigation_fragments:
        findings.append(f"Admin navigation is missing: {missing_navigation_fragments}")

    required_test_fragments = (
        ("Admin", app_test_source),
        ("Admin Controls", smoke_source),
        ("/admin", walkthrough_source),
        ("12-admin-controls.png", screenshots_source),
        ("/api/v1/admin/controls", mock_source),
        ("admin:controls:read", mock_source),
        ("Organization Overview", frontend_test_source),
        ("Safe Admin Workflows", frontend_test_source),
    )
    missing_test_fragments = sorted(
        fragment for fragment, source in required_test_fragments if fragment not in source
    )
    if missing_test_fragments:
        findings.append(f"Admin test coverage is missing: {missing_test_fragments}")

    missing_runtime_signals = sorted(
        signal
        for signal in contract["required_runtime_signals"]
        if signal not in route_source + service_source + frontend_api_source + frontend_page_source
    )
    if missing_runtime_signals:
        findings.append(f"Admin runtime signals are missing: {missing_runtime_signals}")

    required_docs_fragments = (
        ("Admin Controls", admin_runbook_source),
        ("GET /api/v1/admin/controls", admin_runbook_source),
        ("admin:controls:read", admin_runbook_source),
        ("make admin-controls", admin_runbook_source + makefile_source),
        ("check_platform_admin_controls_contract.py", production_runbook_source),
        ("Admin Controls", demo_runbook_source),
        ("Admin controls", evidence_map_source + screenshot_catalog_source),
        ("12-admin-controls.png", screenshot_catalog_source),
    )
    missing_docs_fragments = sorted(
        fragment for fragment, source in required_docs_fragments if fragment not in source
    )
    if missing_docs_fragments:
        findings.append(f"Admin documentation is missing: {missing_docs_fragments}")

    required_release_fragments = (
        "platform_admin_controls_contract",
        "contracts/ops/platform-admin-controls.v1.json",
        "12-admin-controls.png",
    )
    missing_release_fragments = sorted(
        fragment
        for fragment in required_release_fragments
        if fragment not in release_data_source + release_test_source
    )
    if missing_release_fragments:
        findings.append(
            f"Release evidence data is missing admin signals: {missing_release_fragments}"
        )

    if contract["schema_version"] != PLATFORM_ADMIN_CONTROLS_CONTRACT_SCHEMA_VERSION:
        findings.append("Platform admin controls contract schema version is inconsistent.")

    return tuple(findings)


def _read(repo_root: Path, path: str) -> str:
    file_path = repo_root / path
    if not file_path.is_file():
        return ""
    return file_path.read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify the ForgeML platform admin controls contract."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the checked-in platform admin controls contract.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate the checked-in platform admin controls contract.",
    )
    args = parser.parse_args(argv)

    if args.write:
        write_platform_admin_controls_contract(args.output)
        print(f"Wrote platform admin controls contract: {args.output}")
        return 0

    passed, detail = check_platform_admin_controls_contract(args.output)
    print(("PASS " if passed else "FAIL ") + detail)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
