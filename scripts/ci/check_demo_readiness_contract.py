from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

DEMO_READINESS_CONTRACT_SCHEMA_VERSION = "forgeml.demo_readiness_contract.v1"
DEFAULT_OUTPUT_PATH = Path("contracts/ops/demo-readiness.v1.json")
DEFAULT_CI_PATH = Path(".github/workflows/ci.yml")
REPO_ROOT = Path(__file__).resolve().parents[2]


def build_demo_readiness_contract() -> dict[str, Any]:
    return {
        "schema_version": DEMO_READINESS_CONTRACT_SCHEMA_VERSION,
        "generated_from": [
            "scripts.dev.demo_stack",
            "scripts.dev.refresh_demo_data",
            "scripts.examples.bootstrap_examples",
            "frontend.tests.e2e.demo-screenshots",
            "docs.runbooks.demo-readiness",
            "docs.architecture-walkthrough",
        ],
        "operator_commands": [
            "PYTHONPATH=. python scripts/dev/demo_stack.py",
            "PYTHONPATH=. python scripts/dev/demo_stack.py --dry-run",
            (
                "PYTHONPATH=. python scripts/dev/refresh_demo_data.py "
                "--base-url http://127.0.0.1:8001"
            ),
            (
                "npm --prefix frontend exec playwright test "
                "demo-screenshots.spec.ts --project chromium"
            ),
        ],
        "demo_capabilities": [
            "one_command_local_stack",
            "admin_account_seed",
            "seeded_data_refresh",
            "example_project_bootstrap",
            "frontend_screenshot_capture",
            "manual_review_runbook",
            "architecture_walkthrough",
        ],
        "seeded_surfaces": [
            "projects",
            "datasets",
            "feature_store",
            "experiments",
            "training_runs",
            "model_registry",
            "deployments",
            "inference",
            "monitoring",
            "alerts",
            "drift_detection",
            "retraining",
        ],
        "demo_projects": [
            "movie-recommendation",
            "semantic-search",
            "fraud-detection",
        ],
        "quality_gates": [
            "python scripts/ci/check_demo_readiness_contract.py",
            "backend/tests/unit/dev/test_demo_stack.py",
            "backend/tests/unit/dev/test_refresh_demo_data.py",
            "backend/tests/unit/ops/test_demo_readiness_contract.py",
            "frontend/tests/e2e/demo-screenshots.spec.ts",
        ],
    }


def serialize_demo_readiness_contract(contract: dict[str, Any]) -> str:
    return json.dumps(contract, indent=2, sort_keys=True) + "\n"


def write_demo_readiness_contract(output_path: Path = DEFAULT_OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        serialize_demo_readiness_contract(build_demo_readiness_contract()),
        encoding="utf-8",
    )


def check_demo_readiness_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    *,
    ci_path: Path = DEFAULT_CI_PATH,
    repo_root: Path = REPO_ROOT,
) -> tuple[bool, str]:
    findings = list(validate_demo_readiness_definition(repo_root))
    if not output_path.is_file():
        findings.append(f"Demo readiness contract does not exist: {output_path}")
    else:
        expected = serialize_demo_readiness_contract(build_demo_readiness_contract())
        actual = output_path.read_text(encoding="utf-8")
        if actual != expected:
            findings.append(f"Demo readiness contract is stale: {output_path}")

    if not ci_path.is_file():
        findings.append(f"CI workflow does not exist: {ci_path}")
    else:
        ci_source = ci_path.read_text(encoding="utf-8")
        if "python scripts/ci/check_demo_readiness_contract.py" not in ci_source:
            findings.append("Demo readiness contract checker is not wired into CI.")

    if findings:
        return False, "Demo readiness contract violations: " + "; ".join(findings)
    return True, f"Demo readiness contract is current: {output_path}"


def validate_demo_readiness_definition(repo_root: Path = REPO_ROOT) -> tuple[str, ...]:
    required_files = [
        "scripts/dev/demo_stack.py",
        "scripts/dev/refresh_demo_data.py",
        "scripts/examples/bootstrap_examples.py",
        "frontend/tests/e2e/demo-screenshots.spec.ts",
        "docs/runbooks/demo-readiness.md",
        "docs/architecture-walkthrough.md",
        "README.md",
        "Makefile",
    ]
    findings = [
        f"Missing demo readiness file: {path}"
        for path in required_files
        if not (repo_root / path).is_file()
    ]
    if findings:
        return tuple(findings)

    sources = {
        path: (repo_root / path).read_text(encoding="utf-8") for path in required_files
    }
    contract_source = serialize_demo_readiness_contract(build_demo_readiness_contract())
    required_fragments = (
        ("DEMO_STACK_SCHEMA_VERSION", sources["scripts/dev/demo_stack.py"]),
        ("build_demo_plan", sources["scripts/dev/demo_stack.py"]),
        ("build_demo_data_refresh_command", sources["scripts/dev/demo_stack.py"]),
        ("wait_for_http", sources["scripts/dev/demo_stack.py"]),
        ("VITE_FORGEML_API_PROXY_TARGET", sources["scripts/dev/demo_stack.py"]),
        ("DEMO_DATA_REFRESH_SCHEMA_VERSION", sources["scripts/dev/refresh_demo_data.py"]),
        ("refresh_demo_data", sources["scripts/dev/refresh_demo_data.py"]),
        ("forgeml.example_bootstrap_summary.v1", sources["scripts/examples/bootstrap_examples.py"]),
        ("--summary-output", sources["scripts/examples/bootstrap_examples.py"]),
        ("--artifact-root", sources["scripts/examples/bootstrap_examples.py"]),
        (
            "captures reviewer-ready demo screenshots",
            sources["frontend/tests/e2e/demo-screenshots.spec.ts"],
        ),
        ("page.screenshot", sources["frontend/tests/e2e/demo-screenshots.spec.ts"]),
        ("demo-stack", sources["Makefile"]),
        ("demo-refresh", sources["Makefile"]),
        ("demo-screenshots", sources["Makefile"]),
        ("scripts/dev/demo_stack.py", sources["README.md"]),
        ("make demo-stack", sources["docs/runbooks/demo-readiness.md"]),
        ("admin@forgeml.dev", sources["docs/runbooks/demo-readiness.md"]),
        ("modular monolith", sources["docs/architecture-walkthrough.md"].lower()),
        ("one_command_local_stack", contract_source),
        ("seeded_data_refresh", contract_source),
        ("frontend_screenshot_capture", contract_source),
        ("architecture_walkthrough", contract_source),
    )
    missing_fragments = sorted(
        fragment for fragment, source in required_fragments if fragment not in source
    )
    if missing_fragments:
        findings.append(f"Missing demo readiness fragments: {missing_fragments}")

    return tuple(findings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify the ForgeML demo readiness contract."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the checked-in demo readiness contract.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate the checked-in demo readiness contract.",
    )
    args = parser.parse_args(argv)

    if args.write:
        write_demo_readiness_contract(args.output)
        print(f"Wrote demo readiness contract: {args.output}")
        return 0

    passed, detail = check_demo_readiness_contract(args.output)
    print(("PASS " if passed else "FAIL ") + detail)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
