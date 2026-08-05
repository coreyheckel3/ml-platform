from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ops.verify_release_manifest import (  # noqa: E402
    RELEASE_MANIFEST_VERIFICATION_CONTRACT_VERSION,
    RELEASE_MANIFEST_VERIFICATION_SCHEMA_VERSION,
    REQUIRED_VERIFICATION_CHECKS,
    build_release_manifest_verification_contract,
    serialize_release_manifest_verification_contract,
)

DEFAULT_OUTPUT_PATH = Path("contracts/ops/release-manifest-verification.v1.json")
DEFAULT_CI_PATH = Path(".github/workflows/ci.yml")
MINIMUM_REQUIRED_CHECK_COUNT = 8
REQUIRED_VERIFIER_SOURCE_FRAGMENTS = (
    "verify_release_manifest",
    "RELEASE_MANIFEST_SCHEMA_VERSION",
    "REQUIRED_RELEASE_ARTIFACTS",
    "RELEASE_IMAGE_TARGETS",
    "REQUIRED_QUALITY_GATES",
    "RELEASE_EVIDENCE_TYPES",
    "require_ci_evidence",
    "require_image_digests",
    "_sha256_file",
)
REQUIRED_CI_FRAGMENTS = (
    "python scripts/ci/check_release_manifest_verifier_contract.py",
    "python scripts/ops/verify_release_manifest.py",
    "--require-ci-evidence",
)


def write_release_manifest_verification_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        serialize_release_manifest_verification_contract(
            build_release_manifest_verification_contract()
        ),
        encoding="utf-8",
    )


def check_release_manifest_verifier_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    *,
    ci_path: Path = DEFAULT_CI_PATH,
    repo_root: Path = REPO_ROOT,
) -> tuple[bool, str]:
    findings = list(validate_release_manifest_verifier_definition(repo_root))
    if not output_path.is_file():
        findings.append(
            f"Release manifest verification contract does not exist: {output_path}"
        )
    else:
        expected = serialize_release_manifest_verification_contract(
            build_release_manifest_verification_contract()
        )
        actual = output_path.read_text(encoding="utf-8")
        if actual != expected:
            findings.append(
                f"Release manifest verification contract is stale: {output_path}"
            )

    if not ci_path.is_file():
        findings.append(f"CI workflow does not exist: {ci_path}")
    else:
        ci_source = ci_path.read_text(encoding="utf-8")
        missing_fragments = [
            fragment for fragment in REQUIRED_CI_FRAGMENTS if fragment not in ci_source
        ]
        if missing_fragments:
            findings.append(
                "Release manifest verification is not fully wired into CI: "
                f"{missing_fragments}"
            )

    if findings:
        return False, "Release manifest verification contract violations: " + "; ".join(
            findings
        )
    return True, f"Release manifest verification contract is current: {output_path}"


def validate_release_manifest_verifier_definition(
    repo_root: Path = REPO_ROOT,
) -> tuple[str, ...]:
    findings: list[str] = []
    verifier_path = repo_root / "scripts/ops/verify_release_manifest.py"
    if not verifier_path.is_file():
        return (f"Release manifest verifier does not exist: {verifier_path}",)
    verifier_source = verifier_path.read_text(encoding="utf-8")
    missing_fragments = [
        fragment
        for fragment in REQUIRED_VERIFIER_SOURCE_FRAGMENTS
        if fragment not in verifier_source
    ]
    if missing_fragments:
        findings.append(
            f"Release manifest verifier missing source fragments: {missing_fragments}"
        )

    contract = build_release_manifest_verification_contract()
    if contract["schema_version"] != RELEASE_MANIFEST_VERIFICATION_CONTRACT_VERSION:
        findings.append("Release manifest verification contract schema version is inconsistent.")
    if contract["verification_schema_version"] != RELEASE_MANIFEST_VERIFICATION_SCHEMA_VERSION:
        findings.append("Release manifest verification report schema version is inconsistent.")
    if len(REQUIRED_VERIFICATION_CHECKS) < MINIMUM_REQUIRED_CHECK_COUNT:
        findings.append(
            "Release manifest verification must include at least "
            f"{MINIMUM_REQUIRED_CHECK_COUNT} checks."
        )
    if "--require-ci-evidence" not in contract["operator_command"]:
        findings.append("Release manifest verification command must require CI evidence.")
    if "artifact_hash_integrity" not in contract["required_checks"]:
        findings.append("Release manifest verification must check artifact hash integrity.")
    if "dockerfile_hash_integrity" not in contract["required_checks"]:
        findings.append("Release manifest verification must check Dockerfile hash integrity.")

    return tuple(findings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify the ForgeML release manifest verification contract."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the checked-in release manifest verification contract.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate the checked-in release manifest verification contract.",
    )
    args = parser.parse_args(argv)

    if args.write:
        write_release_manifest_verification_contract(args.output)
        print(f"Wrote release manifest verification contract: {args.output}")
        return 0

    passed, detail = check_release_manifest_verifier_contract(args.output)
    print(("PASS " if passed else "FAIL ") + detail)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
