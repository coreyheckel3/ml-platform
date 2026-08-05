from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ops.release_smoke import (  # noqa: E402
    RELEASE_SMOKE_CONTRACT_VERSION,
    RELEASE_SMOKE_STAGE_DEFINITIONS,
    build_release_smoke_contract,
    serialize_release_smoke_contract,
)

DEFAULT_OUTPUT_PATH = Path("contracts/ops/release-smoke.v1.json")
DEFAULT_CI_PATH = Path(".github/workflows/ci.yml")
MINIMUM_REQUIRED_STAGE_COUNT = 16


def write_release_smoke_contract(output_path: Path = DEFAULT_OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        serialize_release_smoke_contract(build_release_smoke_contract()),
        encoding="utf-8",
    )


def check_release_smoke_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    *,
    ci_path: Path = DEFAULT_CI_PATH,
) -> tuple[bool, str]:
    findings = list(validate_release_smoke_definition())
    if not output_path.is_file():
        findings.append(f"Release smoke contract does not exist: {output_path}")
    else:
        expected = serialize_release_smoke_contract(build_release_smoke_contract())
        actual = output_path.read_text(encoding="utf-8")
        if actual != expected:
            findings.append(f"Release smoke contract is stale: {output_path}")

    if not ci_path.is_file():
        findings.append(f"CI workflow does not exist: {ci_path}")
    else:
        ci_source = ci_path.read_text(encoding="utf-8")
        if "python scripts/ci/check_release_smoke_contract.py" not in ci_source:
            findings.append("Release smoke contract checker is not wired into CI.")

    if findings:
        return False, "Release smoke contract violations: " + "; ".join(findings)
    return True, f"Release smoke contract is current: {output_path}"


def validate_release_smoke_definition() -> tuple[str, ...]:
    findings: list[str] = []
    stage_codes = [stage.code for stage in RELEASE_SMOKE_STAGE_DEFINITIONS]
    duplicates = sorted({code for code in stage_codes if stage_codes.count(code) > 1})
    if duplicates:
        findings.append(f"Duplicate release smoke stage codes: {duplicates}")

    required_stages = [stage for stage in RELEASE_SMOKE_STAGE_DEFINITIONS if stage.required]
    if len(required_stages) < MINIMUM_REQUIRED_STAGE_COUNT:
        findings.append(
            "Release smoke must cover at least "
            f"{MINIMUM_REQUIRED_STAGE_COUNT} required control-plane stages."
        )

    mutating_stages = [
        stage.code for stage in RELEASE_SMOKE_STAGE_DEFINITIONS if stage.mutates_data
    ]
    if mutating_stages:
        findings.append(f"Release smoke stages must be non-mutating: {mutating_stages}")

    contract = build_release_smoke_contract()
    if contract["schema_version"] != RELEASE_SMOKE_CONTRACT_VERSION:
        findings.append("Release smoke contract schema version is inconsistent.")
    if not contract["runtime_requirements"]["requires_running_api"]:
        findings.append("Release smoke contract must require a running API.")
    if contract["runtime_requirements"]["mutates_data"]:
        findings.append("Release smoke contract must remain read-only.")

    required_codes = {stage.code for stage in required_stages}
    expected_required = {
        "health_ready",
        "auth_login",
        "auth_identity",
        "project_inventory",
        "dataset_inventory",
        "feature_store_inventory",
        "experiment_inventory",
        "training_inventory",
        "model_registry_inventory",
        "deployment_inventory",
        "inference_endpoint_inventory",
        "monitoring_summary",
        "alert_rule_inventory",
        "alert_event_inventory",
        "drift_report_inventory",
        "retraining_policy_inventory",
        "retraining_run_inventory",
    }
    missing_required = sorted(expected_required - required_codes)
    if missing_required:
        findings.append(f"Release smoke missing required stages: {missing_required}")

    return tuple(findings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify the ForgeML release-candidate smoke contract."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the checked-in release smoke contract.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate the checked-in release smoke contract.",
    )
    args = parser.parse_args(argv)

    if args.write:
        write_release_smoke_contract(args.output)
        print(f"Wrote release smoke contract: {args.output}")
        return 0

    passed, detail = check_release_smoke_contract(args.output)
    print(("PASS " if passed else "FAIL ") + detail)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
