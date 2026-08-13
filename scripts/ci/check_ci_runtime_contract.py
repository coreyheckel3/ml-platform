from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

CI_RUNTIME_CONTRACT_SCHEMA_VERSION = "forgeml.ci_runtime_contract.v1"
DEFAULT_OUTPUT_PATH = Path("contracts/ops/ci-runtime.v1.json")
REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class WorkflowActionPin:
    workflow: str
    action: str
    required_ref: str
    release_checked_at: str


REQUIRED_ACTION_PINS: tuple[WorkflowActionPin, ...] = (
    WorkflowActionPin(
        workflow=".github/workflows/ci.yml",
        action="actions/checkout",
        required_ref="v7",
        release_checked_at="2026-08-12",
    ),
    WorkflowActionPin(
        workflow=".github/workflows/ci.yml",
        action="actions/setup-python",
        required_ref="v7",
        release_checked_at="2026-08-12",
    ),
    WorkflowActionPin(
        workflow=".github/workflows/ci.yml",
        action="actions/setup-node",
        required_ref="v7",
        release_checked_at="2026-08-12",
    ),
    WorkflowActionPin(
        workflow=".github/workflows/ci.yml",
        action="actions/upload-artifact",
        required_ref="v7",
        release_checked_at="2026-08-12",
    ),
    WorkflowActionPin(
        workflow=".github/workflows/terraform-plan.yml",
        action="actions/checkout",
        required_ref="v7",
        release_checked_at="2026-08-12",
    ),
    WorkflowActionPin(
        workflow=".github/workflows/terraform-plan.yml",
        action="hashicorp/setup-terraform",
        required_ref="v4",
        release_checked_at="2026-08-12",
    ),
)

RETIRED_ACTION_REFS = (
    "actions/checkout@v4",
    "actions/setup-node@v4",
    "actions/setup-python@v5",
    "actions/upload-artifact@v4",
    "hashicorp/setup-terraform@v3",
)


def build_ci_runtime_contract() -> dict[str, Any]:
    return {
        "schema_version": CI_RUNTIME_CONTRACT_SCHEMA_VERSION,
        "generated_from": [
            ".github/workflows/ci.yml",
            ".github/workflows/terraform-plan.yml",
            "scripts.ci.check_ci_runtime_contract",
        ],
        "action_pins": [asdict(pin) for pin in REQUIRED_ACTION_PINS],
        "retired_action_refs": list(RETIRED_ACTION_REFS),
        "quality_gates": [
            "python scripts/ci/check_ci_runtime_contract.py",
            "backend/tests/unit/ops/test_ci_runtime_contract.py",
        ],
        "summary": {
            "workflow_count": len({pin.workflow for pin in REQUIRED_ACTION_PINS}),
            "required_action_pin_count": len(REQUIRED_ACTION_PINS),
            "retired_action_ref_count": len(RETIRED_ACTION_REFS),
        },
    }


def serialize_ci_runtime_contract(contract: dict[str, Any]) -> str:
    return json.dumps(contract, indent=2, sort_keys=True) + "\n"


def write_ci_runtime_contract(output_path: Path = DEFAULT_OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        serialize_ci_runtime_contract(build_ci_runtime_contract()),
        encoding="utf-8",
    )


def check_ci_runtime_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    *,
    repo_root: Path = REPO_ROOT,
) -> tuple[bool, str]:
    findings = list(validate_ci_runtime_definition(repo_root))
    if not output_path.is_file():
        findings.append(f"CI runtime contract does not exist: {output_path}")
    else:
        expected = serialize_ci_runtime_contract(build_ci_runtime_contract())
        actual = output_path.read_text(encoding="utf-8")
        if actual != expected:
            findings.append(f"CI runtime contract is stale: {output_path}")

    if findings:
        return False, "CI runtime contract violations: " + "; ".join(findings)
    return True, f"CI runtime contract is current: {output_path}"


def validate_ci_runtime_definition(repo_root: Path = REPO_ROOT) -> tuple[str, ...]:
    findings: list[str] = []
    workflows = sorted({pin.workflow for pin in REQUIRED_ACTION_PINS})
    for workflow in workflows:
        workflow_path = repo_root / workflow
        if not workflow_path.is_file():
            findings.append(f"Missing CI workflow: {workflow}")
            continue
        workflow_source = workflow_path.read_text(encoding="utf-8")
        workflow_pins = [pin for pin in REQUIRED_ACTION_PINS if pin.workflow == workflow]
        findings.extend(validate_workflow_action_pins(workflow, workflow_source, workflow_pins))

    ci_source = (repo_root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    if "python scripts/ci/check_ci_runtime_contract.py" not in ci_source:
        findings.append("CI runtime contract checker is not wired into CI.")

    docs_source = (repo_root / "outputs/forgeml/docs/14-ci-cd-strategy.md").read_text(
        encoding="utf-8"
    )
    if "CI runtime contract" not in docs_source:
        findings.append("CI/CD strategy does not document the CI runtime contract.")

    return tuple(findings)


def validate_workflow_action_pins(
    workflow: str,
    workflow_source: str,
    required_pins: list[WorkflowActionPin],
) -> tuple[str, ...]:
    findings: list[str] = []
    for pin in required_pins:
        expected = f"{pin.action}@{pin.required_ref}"
        if expected not in workflow_source:
            findings.append(f"{workflow} must use {expected}.")
    retired_refs = [
        action_ref for action_ref in RETIRED_ACTION_REFS if action_ref in workflow_source
    ]
    if retired_refs:
        findings.append(f"{workflow} contains retired action refs: {retired_refs}")
    floating_refs = sorted(
        re.findall(
            r"uses:\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)@(main|master)",
            workflow_source,
        )
    )
    if floating_refs:
        findings.append(f"{workflow} contains floating action refs: {floating_refs}")
    return tuple(findings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify ForgeML GitHub Actions runtime pins."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the checked-in CI runtime contract.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate the checked-in CI runtime contract.",
    )
    args = parser.parse_args(argv)

    if args.write:
        write_ci_runtime_contract(args.output)
        print(f"Wrote CI runtime contract: {args.output}")
        return 0

    passed, detail = check_ci_runtime_contract(args.output)
    print(("PASS " if passed else "FAIL ") + detail)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
