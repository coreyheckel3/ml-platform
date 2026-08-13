from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PORTFOLIO_READINESS_CONTRACT_SCHEMA_VERSION = "forgeml.portfolio_readiness_contract.v1"
DEFAULT_OUTPUT_PATH = Path("contracts/ops/portfolio-readiness.v1.json")
DEFAULT_CI_PATH = Path(".github/workflows/ci.yml")
REPO_ROOT = Path(__file__).resolve().parents[2]

PORTFOLIO_ASSETS = (
    "docs/portfolio/README.md",
    "docs/portfolio/reviewer-guide.md",
    "docs/portfolio/resume-bullets.md",
    "docs/portfolio/evidence-map.md",
    "docs/portfolio/architecture-diagrams.md",
    "docs/portfolio/screenshot-catalog.md",
)


def build_portfolio_readiness_contract() -> dict[str, Any]:
    return {
        "schema_version": PORTFOLIO_READINESS_CONTRACT_SCHEMA_VERSION,
        "generated_from": [
            "docs.portfolio.README",
            "docs.portfolio.reviewer-guide",
            "docs.portfolio.resume-bullets",
            "docs.portfolio.evidence-map",
            "docs.portfolio.architecture-diagrams",
            "docs.portfolio.screenshot-catalog",
        ],
        "reviewer_assets": [
            {
                "name": "portfolio_index",
                "path": "docs/portfolio/README.md",
                "required_fragments": [
                    "ForgeML Portfolio Review Kit",
                    "reviewer-guide.md",
                    "resume-bullets.md",
                    "evidence-map.md",
                    "architecture-diagrams.md",
                    "screenshot-catalog.md",
                ],
            },
            {
                "name": "reviewer_guide",
                "path": "docs/portfolio/reviewer-guide.md",
                "required_fragments": [
                    "ForgeML is an end-to-end ML platform control plane",
                    "make demo-stack",
                    "make production-readiness",
                    "release-governance loop",
                ],
            },
            {
                "name": "resume_bullets",
                "path": "docs/portfolio/resume-bullets.md",
                "required_fragments": [
                    "ML Engineer",
                    "MLOps Engineer",
                    "AI Platform Engineer",
                    "Backend / Platform Engineer",
                    "Short Project Summary",
                ],
            },
            {
                "name": "evidence_map",
                "path": "docs/portfolio/evidence-map.md",
                "required_fragments": [
                    "Modular monolith with clean boundaries",
                    "Artifact storage abstraction",
                    "MLflow integration boundary",
                    "Airflow orchestration boundary",
                    "Portfolio assets under contract",
                ],
            },
            {
                "name": "architecture_diagrams",
                "path": "docs/portfolio/architecture-diagrams.md",
                "required_fragments": [
                    "```mermaid",
                    "Modular Monolith",
                    "ML Lifecycle",
                    "Monitoring To Retraining",
                    "Release Governance",
                ],
            },
            {
                "name": "screenshot_catalog",
                "path": "docs/portfolio/screenshot-catalog.md",
                "required_fragments": [
                    "make demo-screenshots",
                    "01-dashboard.png",
                    "04-training-runs.png",
                    "08-monitoring.png",
                    "Navigate to each screenshot route explicitly",
                ],
            },
        ],
        "portfolio_claims": [
            "multi_project_ml_platform",
            "modular_monolith_architecture",
            "mlops_release_governance",
            "adapter_boundaries",
            "tenant_aware_security",
            "browser_verified_demo",
        ],
        "operator_commands": [
            "PYTHONPATH=. python scripts/ci/check_portfolio_readiness_contract.py",
            "make demo-stack",
            "make demo-screenshots",
            "make production-readiness",
        ],
        "quality_gates": [
            "python scripts/ci/check_portfolio_readiness_contract.py",
            "backend/tests/unit/ops/test_portfolio_readiness_contract.py",
            "backend/tests/unit/ops/test_production_readiness_assets.py",
        ],
        "summary": {
            "reviewer_asset_count": len(PORTFOLIO_ASSETS),
            "portfolio_claim_count": 6,
        },
    }


def serialize_portfolio_readiness_contract(contract: dict[str, Any]) -> str:
    return json.dumps(contract, indent=2, sort_keys=True) + "\n"


def write_portfolio_readiness_contract(output_path: Path = DEFAULT_OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        serialize_portfolio_readiness_contract(build_portfolio_readiness_contract()),
        encoding="utf-8",
    )


def check_portfolio_readiness_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    *,
    ci_path: Path = DEFAULT_CI_PATH,
    repo_root: Path = REPO_ROOT,
) -> tuple[bool, str]:
    findings = list(validate_portfolio_readiness_definition(repo_root))
    if not output_path.is_file():
        findings.append(f"Portfolio readiness contract does not exist: {output_path}")
    else:
        expected = serialize_portfolio_readiness_contract(
            build_portfolio_readiness_contract()
        )
        actual = output_path.read_text(encoding="utf-8")
        if actual != expected:
            findings.append(f"Portfolio readiness contract is stale: {output_path}")

    if not ci_path.is_file():
        findings.append(f"CI workflow does not exist: {ci_path}")
    else:
        ci_source = ci_path.read_text(encoding="utf-8")
        if "python scripts/ci/check_portfolio_readiness_contract.py" not in ci_source:
            findings.append("Portfolio readiness contract checker is not wired into CI.")

    if findings:
        return False, "Portfolio readiness contract violations: " + "; ".join(findings)
    return True, f"Portfolio readiness contract is current: {output_path}"


def validate_portfolio_readiness_definition(
    repo_root: Path = REPO_ROOT,
) -> tuple[str, ...]:
    findings: list[str] = []
    contract = build_portfolio_readiness_contract()
    for asset in contract["reviewer_assets"]:
        asset_path = repo_root / asset["path"]
        if not asset_path.is_file():
            findings.append(f"Missing portfolio asset: {asset['path']}")
            continue
        source = asset_path.read_text(encoding="utf-8")
        missing_fragments = [
            fragment
            for fragment in asset["required_fragments"]
            if fragment not in source
        ]
        if missing_fragments:
            findings.append(
                f"Portfolio asset {asset['path']} is missing fragments: "
                f"{missing_fragments}"
            )

    if len(contract["reviewer_assets"]) != len(PORTFOLIO_ASSETS):
        findings.append("Portfolio readiness contract asset count is inconsistent.")
    if contract["schema_version"] != PORTFOLIO_READINESS_CONTRACT_SCHEMA_VERSION:
        findings.append("Portfolio readiness contract schema version is inconsistent.")

    return tuple(findings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify the ForgeML portfolio readiness contract."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the checked-in portfolio readiness contract.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate the checked-in portfolio readiness contract.",
    )
    args = parser.parse_args(argv)

    if args.write:
        write_portfolio_readiness_contract(args.output)
        print(f"Wrote portfolio readiness contract: {args.output}")
        return 0

    passed, detail = check_portfolio_readiness_contract(args.output)
    print(("PASS " if passed else "FAIL ") + detail)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
