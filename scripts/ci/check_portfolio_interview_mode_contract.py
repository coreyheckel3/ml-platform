from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PORTFOLIO_INTERVIEW_MODE_CONTRACT_SCHEMA_VERSION = (
    "forgeml.portfolio_interview_mode_contract.v1"
)
DEFAULT_OUTPUT_PATH = Path("contracts/ops/portfolio-interview-mode.v1.json")
DEFAULT_CI_PATH = Path(".github/workflows/ci.yml")
REPO_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_SOURCE_ASSETS = (
    "frontend/src/modules/portfolio/data/interviewMode.ts",
    "frontend/src/modules/portfolio/pages/PortfolioInterviewPage.tsx",
    "frontend/src/modules/portfolio/pages/PortfolioInterviewPage.test.tsx",
    "frontend/src/app/navigation.ts",
    "frontend/src/app/routes.tsx",
    "frontend/tests/e2e/demo-walkthrough.spec.ts",
    "frontend/tests/e2e/demo-screenshots.spec.ts",
    "frontend/tests/e2e/smoke.spec.ts",
    "Makefile",
    "docs/portfolio/interview-mode.md",
    "docs/portfolio/README.md",
    "docs/portfolio/reviewer-guide.md",
    "docs/portfolio/evidence-map.md",
    "docs/portfolio/screenshot-catalog.md",
)


def build_portfolio_interview_mode_contract() -> dict[str, Any]:
    return {
        "schema_version": PORTFOLIO_INTERVIEW_MODE_CONTRACT_SCHEMA_VERSION,
        "generated_from": [
            "frontend.modules.portfolio",
            "frontend.app.navigation",
            "frontend.app.routes",
            "frontend.tests.e2e.demo-walkthrough",
            "frontend.tests.e2e.demo-screenshots",
            "docs.portfolio.interview-mode",
        ],
        "route": {
            "path": "/portfolio",
            "label": "Portfolio",
            "navigation_icon": "Presentation",
        },
        "required_source_assets": list(REQUIRED_SOURCE_ASSETS),
        "required_ui_sections": [
            "Reviewer Dashboard",
            "Architecture Walkthrough",
            "Evidence Explanations",
            "Validation Paths",
            "Interview Talk Track",
            "Portfolio Evidence Contract",
        ],
        "required_interview_signals": [
            "Portfolio Interview Mode",
            "Multi-project ML platform",
            "modular monolith",
            "conversational-movie-recommender",
            "release-governance loop",
            "make demo-stack-fresh",
            "make demo-walkthrough",
            "make demo-screenshots",
            "make production-readiness",
            "portfolio_interview_mode_contract",
            "contracts/ops/portfolio-interview-mode.v1.json",
            "docs/portfolio/interview-mode.md",
            "11-portfolio-interview-mode.png",
        ],
        "operator_commands": [
            "PYTHONPATH=. python scripts/ci/check_portfolio_interview_mode_contract.py",
            "make portfolio-interview",
            "make demo-stack-fresh",
            "make demo-walkthrough",
            "make demo-screenshots",
            "make production-readiness",
        ],
        "quality_gates": [
            "python scripts/ci/check_portfolio_interview_mode_contract.py",
            "backend/tests/unit/ops/test_portfolio_interview_mode_contract.py",
            "frontend/src/modules/portfolio/pages/PortfolioInterviewPage.test.tsx",
            "frontend/tests/e2e/demo-walkthrough.spec.ts",
            "frontend/tests/e2e/demo-screenshots.spec.ts",
        ],
        "summary": {
            "source_asset_count": len(REQUIRED_SOURCE_ASSETS),
            "ui_section_count": 6,
            "interview_signal_count": 13,
        },
    }


def serialize_portfolio_interview_mode_contract(contract: dict[str, Any]) -> str:
    return json.dumps(contract, indent=2, sort_keys=True) + "\n"


def write_portfolio_interview_mode_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        serialize_portfolio_interview_mode_contract(
            build_portfolio_interview_mode_contract()
        ),
        encoding="utf-8",
    )


def check_portfolio_interview_mode_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    *,
    ci_path: Path = DEFAULT_CI_PATH,
    repo_root: Path = REPO_ROOT,
) -> tuple[bool, str]:
    findings = list(validate_portfolio_interview_mode_definition(repo_root))
    if not output_path.is_file():
        findings.append(f"Portfolio interview mode contract does not exist: {output_path}")
    else:
        expected = serialize_portfolio_interview_mode_contract(
            build_portfolio_interview_mode_contract()
        )
        actual = output_path.read_text(encoding="utf-8")
        if actual != expected:
            findings.append(f"Portfolio interview mode contract is stale: {output_path}")

    if not ci_path.is_file():
        findings.append(f"CI workflow does not exist: {ci_path}")
    else:
        ci_source = ci_path.read_text(encoding="utf-8")
        if "python scripts/ci/check_portfolio_interview_mode_contract.py" not in ci_source:
            findings.append("Portfolio interview mode contract checker is not wired into CI.")

    if findings:
        return False, "Portfolio interview mode violations: " + "; ".join(findings)
    return True, f"Portfolio interview mode contract is current: {output_path}"


def validate_portfolio_interview_mode_definition(
    repo_root: Path = REPO_ROOT,
) -> tuple[str, ...]:
    findings: list[str] = []
    contract = build_portfolio_interview_mode_contract()

    for source_asset in contract["required_source_assets"]:
        asset_path = repo_root / source_asset
        if not asset_path.is_file():
            findings.append(f"Missing portfolio interview source asset: {source_asset}")

    page_source = _read(
        repo_root, "frontend/src/modules/portfolio/pages/PortfolioInterviewPage.tsx"
    )
    page_test_source = _read(
        repo_root, "frontend/src/modules/portfolio/pages/PortfolioInterviewPage.test.tsx"
    )
    data_source = _read(repo_root, "frontend/src/modules/portfolio/data/interviewMode.ts")
    routes_source = _read(repo_root, "frontend/src/app/routes.tsx")
    navigation_source = _read(repo_root, "frontend/src/app/navigation.ts")
    smoke_source = _read(repo_root, "frontend/tests/e2e/smoke.spec.ts")
    walkthrough_source = _read(repo_root, "frontend/tests/e2e/demo-walkthrough.spec.ts")
    screenshots_source = _read(repo_root, "frontend/tests/e2e/demo-screenshots.spec.ts")
    interview_doc_source = _read(repo_root, "docs/portfolio/interview-mode.md")
    makefile_source = _read(repo_root, "Makefile")
    portfolio_index_source = _read(repo_root, "docs/portfolio/README.md")
    reviewer_guide_source = _read(repo_root, "docs/portfolio/reviewer-guide.md")
    evidence_map_source = _read(repo_root, "docs/portfolio/evidence-map.md")
    screenshot_catalog_source = _read(repo_root, "docs/portfolio/screenshot-catalog.md")

    page_fragments = [
        contract["route"]["path"],
        "Portfolio Interview Mode",
        *contract["required_ui_sections"],
        *contract["required_interview_signals"],
    ]
    missing_page_fragments = [
        fragment for fragment in page_fragments if fragment not in page_source + data_source
    ]
    if missing_page_fragments:
        findings.append(
            f"Portfolio interview page is missing fragments: {missing_page_fragments}"
        )

    route_fragments = [
        'path: "/portfolio"',
        "loadPortfolioInterviewPage",
        "PortfolioInterviewPage",
    ]
    missing_route_fragments = [
        fragment for fragment in route_fragments if fragment not in routes_source
    ]
    if missing_route_fragments:
        findings.append(f"Portfolio route is missing fragments: {missing_route_fragments}")

    navigation_fragments = [
        'label: "Portfolio"',
        'path: "/portfolio"',
        "Presentation",
    ]
    missing_navigation_fragments = [
        fragment for fragment in navigation_fragments if fragment not in navigation_source
    ]
    if missing_navigation_fragments:
        findings.append(
            f"Portfolio navigation is missing fragments: {missing_navigation_fragments}"
        )

    required_test_fragments = (
        ("Portfolio Interview Mode", page_test_source),
        ("portfolio_interview_mode_contract", page_test_source),
        ("make demo-stack-fresh", page_test_source),
        ("11-portfolio-interview-mode.png", page_test_source),
        ("Portfolio", smoke_source),
        ("portfolio-interview", makefile_source),
        ("/portfolio", walkthrough_source),
        ("11-portfolio-interview-mode.png", screenshots_source),
    )
    missing_test_fragments = sorted(
        fragment for fragment, source in required_test_fragments if fragment not in source
    )
    if missing_test_fragments:
        findings.append(
            f"Portfolio interview tests are missing fragments: {missing_test_fragments}"
        )

    doc_fragments = (
        ("Portfolio Interview Mode", interview_doc_source),
        ("Reviewer Dashboard", interview_doc_source),
        ("Architecture Walkthrough", interview_doc_source),
        ("Validation Paths", interview_doc_source),
        ("portfolio_interview_mode_contract", interview_doc_source),
        ("interview-mode.md", portfolio_index_source),
        ("/portfolio", reviewer_guide_source),
        ("make portfolio-interview", reviewer_guide_source),
        ("Portfolio interview mode", evidence_map_source),
        ("11-portfolio-interview-mode.png", screenshot_catalog_source),
    )
    missing_doc_fragments = sorted(
        fragment for fragment, source in doc_fragments if fragment not in source
    )
    if missing_doc_fragments:
        findings.append(
            f"Portfolio interview docs are missing fragments: {missing_doc_fragments}"
        )

    if contract["schema_version"] != PORTFOLIO_INTERVIEW_MODE_CONTRACT_SCHEMA_VERSION:
        findings.append("Portfolio interview mode schema version is inconsistent.")

    return tuple(findings)


def _read(repo_root: Path, path: str) -> str:
    file_path = repo_root / path
    if not file_path.is_file():
        return ""
    return file_path.read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify the ForgeML portfolio interview mode contract."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the checked-in portfolio interview mode contract.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate the checked-in portfolio interview mode contract.",
    )
    args = parser.parse_args(argv)

    if args.write:
        write_portfolio_interview_mode_contract(args.output)
        print(f"Wrote portfolio interview mode contract: {args.output}")
        return 0

    passed, detail = check_portfolio_interview_mode_contract(args.output)
    print(("PASS " if passed else "FAIL ") + detail)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
