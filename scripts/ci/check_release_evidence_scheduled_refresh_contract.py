from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

RELEASE_EVIDENCE_SCHEDULED_REFRESH_CONTRACT_SCHEMA_VERSION = (
    "forgeml.release_evidence_scheduled_refresh_contract.v1"
)
DEFAULT_OUTPUT_PATH = Path("contracts/ops/release-evidence-scheduled-refresh.v1.json")
DEFAULT_CI_PATH = Path(".github/workflows/ci.yml")
REPO_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_ENDPOINTS = (("GET", "/api/v1/admin/release-evidence/refresh/status"),)
REQUIRED_PERMISSIONS = ("admin:release_evidence:read",)
REQUIRED_STALE_REASONS = (
    "no_reports",
    "no_successful_report",
    "last_success_older_than_threshold",
    "latest_report_failed",
)
REQUIRED_SOURCE_ASSETS = (
    "backend/src/forgeml/modules/administration/application/services.py",
    "backend/src/forgeml/modules/administration/api/routes.py",
    "backend/src/forgeml/modules/administration/api/schemas.py",
    "backend/src/forgeml/platform/config.py",
    "backend/src/forgeml/platform/release_evidence/retrieval.py",
    "backend/tests/api/test_administration_api.py",
    "backend/tests/unit/administration/test_administration_service.py",
    "backend/tests/unit/ops/test_release_evidence_refresh.py",
    "frontend/src/modules/release_evidence/api/releaseEvidence.ts",
    "frontend/src/modules/release_evidence/data/releaseEvidence.ts",
    "frontend/src/modules/release_evidence/pages/ReleaseEvidencePage.tsx",
    "frontend/src/modules/release_evidence/pages/ReleaseEvidencePage.test.tsx",
    "frontend/tests/e2e/fixtures/forgemlApiMock.ts",
    "scripts/ops/refresh_release_evidence.py",
    "scripts/ops/build_release_manifest.py",
    "scripts/ci/production_readiness.py",
    "contracts/openapi/forgeml.v1.openapi.json",
    "docs/runbooks/production-readiness.md",
    "docs/portfolio/evidence-map.md",
    "docs/portfolio/reviewer-guide.md",
    "contracts/ops/README.md",
    "README.md",
)


def build_release_evidence_scheduled_refresh_contract() -> dict[str, Any]:
    return {
        "schema_version": RELEASE_EVIDENCE_SCHEDULED_REFRESH_CONTRACT_SCHEMA_VERSION,
        "generated_from": [
            "forgeml.modules.administration",
            "frontend.modules.release_evidence",
            "scripts.ops.refresh_release_evidence",
        ],
        "api": {
            "endpoints": [
                {"method": method, "path": path} for method, path in REQUIRED_ENDPOINTS
            ],
            "response_model": "ReleaseEvidenceRefreshStatusResponse",
            "schema_version": "forgeml.release_evidence_refresh_status.v1",
            "permission": "admin:release_evidence:read",
        },
        "automation": {
            "script": "scripts/ops/refresh_release_evidence.py",
            "report_schema_version": "forgeml.release_evidence_refresh.v1",
            "modes": ["one_shot", "scheduled_loop", "dry_run", "forced_refresh"],
            "required_flags": [
                "--base-url",
                "--access-token",
                "--email",
                "--password",
                "--stale-after-seconds",
                "--refresh-interval-seconds",
                "--interval-seconds",
                "--max-runs",
                "--once",
                "--dry-run",
                "--force",
                "--print-cron",
            ],
        },
        "stale_semantics": {
            "default_stale_after_seconds": 86_400,
            "default_refresh_interval_seconds": 3_600,
            "reasons": list(REQUIRED_STALE_REASONS),
            "statuses": ["fresh", "attention", "stale", "missing"],
            "actions": ["wait_until_next_refresh", "retrieve_now"],
        },
        "ui": {
            "route": "/release-evidence",
            "section": "Scheduled Refresh",
            "signals": [
                "Last Success Summary",
                "Stale Indicators",
                "Scheduled Command",
            ],
        },
        "required_source_assets": list(REQUIRED_SOURCE_ASSETS),
        "quality_gates": [
            "python scripts/ci/check_release_evidence_scheduled_refresh_contract.py",
            "backend/tests/api/test_administration_api.py",
            "backend/tests/unit/administration/test_administration_service.py",
            "backend/tests/unit/ops/test_release_evidence_refresh.py",
            "frontend/src/modules/release_evidence/pages/ReleaseEvidencePage.test.tsx",
        ],
        "release_manifest": {
            "artifact_name": "release_evidence_scheduled_refresh_contract",
            "quality_gate_name": "release_evidence_scheduled_refresh_contract",
        },
        "summary": {
            "endpoint_count": len(REQUIRED_ENDPOINTS),
            "source_asset_count": len(REQUIRED_SOURCE_ASSETS),
            "stale_reason_count": len(REQUIRED_STALE_REASONS),
        },
    }


def serialize_release_evidence_scheduled_refresh_contract(
    contract: dict[str, Any],
) -> str:
    return json.dumps(contract, indent=2, sort_keys=True) + "\n"


def write_release_evidence_scheduled_refresh_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        serialize_release_evidence_scheduled_refresh_contract(
            build_release_evidence_scheduled_refresh_contract()
        ),
        encoding="utf-8",
    )


def check_release_evidence_scheduled_refresh_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    *,
    ci_path: Path = DEFAULT_CI_PATH,
    repo_root: Path = REPO_ROOT,
) -> tuple[bool, str]:
    findings = list(validate_release_evidence_scheduled_refresh_definition(repo_root))
    if not output_path.is_file():
        findings.append(
            f"Release evidence scheduled refresh contract does not exist: {output_path}"
        )
    else:
        expected = serialize_release_evidence_scheduled_refresh_contract(
            build_release_evidence_scheduled_refresh_contract()
        )
        actual = output_path.read_text(encoding="utf-8")
        if actual != expected:
            findings.append(
                f"Release evidence scheduled refresh contract is stale: {output_path}"
            )

    if not ci_path.is_file():
        findings.append(f"CI workflow does not exist: {ci_path}")
    else:
        ci_source = ci_path.read_text(encoding="utf-8")
        if (
            "python scripts/ci/check_release_evidence_scheduled_refresh_contract.py"
            not in ci_source
        ):
            findings.append("Release evidence scheduled refresh checker is not wired into CI.")

    if findings:
        return False, "Release evidence scheduled refresh violations: " + "; ".join(
            findings
        )
    return True, f"Release evidence scheduled refresh contract is current: {output_path}"


def validate_release_evidence_scheduled_refresh_definition(
    repo_root: Path = REPO_ROOT,
) -> tuple[str, ...]:
    findings: list[str] = []
    contract = build_release_evidence_scheduled_refresh_contract()
    for source_asset in contract["required_source_assets"]:
        if not (repo_root / source_asset).is_file():
            findings.append(f"Missing scheduled refresh asset: {source_asset}")

    service_source = _read(
        repo_root,
        "backend/src/forgeml/modules/administration/application/services.py",
    )
    routes_source = _read(repo_root, "backend/src/forgeml/modules/administration/api/routes.py")
    schemas_source = _read(
        repo_root,
        "backend/src/forgeml/modules/administration/api/schemas.py",
    )
    config_source = _read(repo_root, "backend/src/forgeml/platform/config.py")
    runtime_source = _read(
        repo_root,
        "backend/src/forgeml/platform/release_evidence/retrieval.py",
    )
    cli_source = _read(repo_root, "scripts/ops/refresh_release_evidence.py")
    frontend_api_source = _read(
        repo_root,
        "frontend/src/modules/release_evidence/api/releaseEvidence.ts",
    )
    frontend_data_source = _read(
        repo_root,
        "frontend/src/modules/release_evidence/data/releaseEvidence.ts",
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
    manifest_builder_source = _read(repo_root, "scripts/ops/build_release_manifest.py")
    ci_source = _read(repo_root, ".github/workflows/ci.yml")
    runbook_source = _read(repo_root, "docs/runbooks/production-readiness.md")
    evidence_map_source = _read(repo_root, "docs/portfolio/evidence-map.md")
    reviewer_guide_source = _read(repo_root, "docs/portfolio/reviewer-guide.md")
    ops_readme_source = _read(repo_root, "contracts/ops/README.md")
    readme_source = _read(repo_root, "README.md")
    openapi_contract = _read_json(repo_root / "contracts/openapi/forgeml.v1.openapi.json")

    _require_fragments(
        findings,
        "administration service",
        service_source,
        (
            "GetReleaseEvidenceRefreshStatusQuery",
            "ReleaseEvidenceRefreshStatus",
            "get_release_evidence_refresh_status",
            "last_success_older_than_threshold",
            "latest_report_failed",
            "_refresh_operator_command",
        ),
    )
    _require_fragments(
        findings,
        "administration routes",
        routes_source,
        (
            '"/admin/release-evidence/refresh/status"',
            "GetReleaseEvidenceRefreshStatusQuery",
            "ReleaseEvidenceRefreshStatusResponse",
        ),
    )
    _require_fragments(
        findings,
        "administration schemas",
        schemas_source,
        (
            "ReleaseEvidenceRefreshStatusResponse",
            "forgeml.release_evidence_refresh_status.v1",
            "last_successful_report",
        ),
    )
    _require_fragments(
        findings,
        "runtime config",
        config_source,
        (
            "FORGEML_RELEASE_EVIDENCE_STALE_AFTER_SECONDS",
            "FORGEML_RELEASE_EVIDENCE_REFRESH_INTERVAL_SECONDS",
        ),
    )
    _require_fragments(
        findings,
        "release evidence runtime",
        runtime_source,
        ("release_evidence_scheduled_refresh_contract",),
    )
    _require_fragments(
        findings,
        "refresh CLI",
        cli_source,
        (
            "forgeml.release_evidence_refresh.v1",
            "ReleaseEvidenceRefreshClient",
            "run_release_evidence_refresh_once",
            "--stale-after-seconds",
            "--refresh-interval-seconds",
            "--interval-seconds",
            "--print-cron",
            "api_recommended_retrieve_now",
        ),
    )
    _require_fragments(
        findings,
        "frontend API client",
        frontend_api_source,
        ("ReleaseEvidenceRefreshStatus", "getReleaseEvidenceRefreshStatus"),
    )
    _require_fragments(
        findings,
        "frontend data",
        frontend_data_source,
        (
            "scheduledReleaseEvidenceRefresh",
            "release_evidence_scheduled_refresh_contract",
            "Release Evidence Scheduled Refresh Contract",
        ),
    )
    _require_fragments(
        findings,
        "release evidence page",
        page_source,
        (
            "Scheduled Refresh",
            "Last Success Summary",
            "Stale Indicators",
            "Scheduled Command",
        ),
    )
    _require_fragments(
        findings,
        "release evidence page test",
        page_test_source,
        (
            "releaseEvidenceRefreshStatus",
            "latest_report_failed",
            "Release Evidence Scheduled Refresh Contract",
        ),
    )
    _require_fragments(
        findings,
        "Playwright API mock",
        e2e_mock_source,
        (
            "/api/v1/admin/release-evidence/refresh/status",
            "releaseEvidenceRefreshStatus",
        ),
    )
    _require_fragments(
        findings,
        "production readiness",
        production_readiness_source,
        ("check_release_evidence_scheduled_refresh_contract",),
    )
    _require_fragments(
        findings,
        "CI workflow",
        ci_source,
        ("python scripts/ci/check_release_evidence_scheduled_refresh_contract.py",),
    )
    _require_fragments(
        findings,
        "release manifest builder",
        manifest_builder_source,
        ("release_evidence_scheduled_refresh_contract",),
    )
    _require_fragments(
        findings,
        "production readiness runbook",
        runbook_source,
        ("refresh_release_evidence.py",),
    )
    _require_fragments(
        findings,
        "portfolio evidence map",
        evidence_map_source,
        ("Release evidence scheduled refresh",),
    )
    _require_fragments(
        findings,
        "portfolio reviewer guide",
        reviewer_guide_source,
        ("check_release_evidence_scheduled_refresh_contract.py",),
    )
    _require_fragments(
        findings,
        "operations contracts README",
        ops_readme_source,
        ("release-evidence-scheduled-refresh.v1.json",),
    )
    _require_fragments(
        findings,
        "README",
        readme_source,
        ("refresh_release_evidence.py",),
    )

    paths = openapi_contract.get("paths", {}) if openapi_contract else {}
    if isinstance(paths, dict):
        for method, path in REQUIRED_ENDPOINTS:
            operations = paths.get(path)
            if not isinstance(operations, dict) or method.lower() not in operations:
                findings.append(f"OpenAPI contract is missing {method} {path}.")

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
        description="Verify the ForgeML release evidence scheduled refresh contract."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the checked-in release evidence scheduled refresh contract.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate the checked-in release evidence scheduled refresh contract.",
    )
    args = parser.parse_args(argv)

    if args.write:
        write_release_evidence_scheduled_refresh_contract(args.output)
        return 0

    passed, detail = check_release_evidence_scheduled_refresh_contract(args.output)
    print(detail)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
