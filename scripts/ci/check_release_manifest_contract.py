from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ops.build_release_manifest import (  # noqa: E402
    RELEASE_IMAGE_TARGETS,
    RELEASE_MANIFEST_CONTRACT_VERSION,
    REQUIRED_QUALITY_GATES,
    REQUIRED_RELEASE_ARTIFACTS,
    build_release_manifest_contract,
    serialize_release_manifest_contract,
)

DEFAULT_OUTPUT_PATH = Path("contracts/ops/release-manifest.v1.json")
DEFAULT_CI_PATH = Path(".github/workflows/ci.yml")
MINIMUM_REQUIRED_ARTIFACT_COUNT = 14
MINIMUM_IMAGE_TARGET_COUNT = 5


def write_release_manifest_contract(output_path: Path = DEFAULT_OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        serialize_release_manifest_contract(build_release_manifest_contract()),
        encoding="utf-8",
    )


def check_release_manifest_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    *,
    ci_path: Path = DEFAULT_CI_PATH,
    repo_root: Path = REPO_ROOT,
) -> tuple[bool, str]:
    findings = list(validate_release_manifest_definition(repo_root))
    if not output_path.is_file():
        findings.append(f"Release manifest contract does not exist: {output_path}")
    else:
        expected = serialize_release_manifest_contract(build_release_manifest_contract())
        actual = output_path.read_text(encoding="utf-8")
        if actual != expected:
            findings.append(f"Release manifest contract is stale: {output_path}")

    if not ci_path.is_file():
        findings.append(f"CI workflow does not exist: {ci_path}")
    else:
        ci_source = ci_path.read_text(encoding="utf-8")
        if "python scripts/ci/check_release_manifest_contract.py" not in ci_source:
            findings.append("Release manifest contract checker is not wired into CI.")

    if findings:
        return False, "Release manifest contract violations: " + "; ".join(findings)
    return True, f"Release manifest contract is current: {output_path}"


def validate_release_manifest_definition(repo_root: Path = REPO_ROOT) -> tuple[str, ...]:
    findings: list[str] = []
    artifact_names = [artifact.name for artifact in REQUIRED_RELEASE_ARTIFACTS]
    artifact_paths = [artifact.path for artifact in REQUIRED_RELEASE_ARTIFACTS]
    image_names = [image.name for image in RELEASE_IMAGE_TARGETS]

    duplicate_artifacts = sorted(
        {name for name in artifact_names if artifact_names.count(name) > 1}
    )
    duplicate_paths = sorted({path for path in artifact_paths if artifact_paths.count(path) > 1})
    duplicate_images = sorted({name for name in image_names if image_names.count(name) > 1})
    if duplicate_artifacts:
        findings.append(f"Duplicate release artifact names: {duplicate_artifacts}")
    if duplicate_paths:
        findings.append(f"Duplicate release artifact paths: {duplicate_paths}")
    if duplicate_images:
        findings.append(f"Duplicate image target names: {duplicate_images}")

    required_artifacts = [artifact for artifact in REQUIRED_RELEASE_ARTIFACTS if artifact.required]
    if len(required_artifacts) < MINIMUM_REQUIRED_ARTIFACT_COUNT:
        findings.append(
            "Release manifest must include at least "
            f"{MINIMUM_REQUIRED_ARTIFACT_COUNT} required artifacts."
        )

    if len(RELEASE_IMAGE_TARGETS) < MINIMUM_IMAGE_TARGET_COUNT:
        findings.append(
            "Release manifest must include at least "
            f"{MINIMUM_IMAGE_TARGET_COUNT} image targets."
        )

    missing_artifact_paths = sorted(
        artifact.path
        for artifact in required_artifacts
        if not (repo_root / artifact.path).is_file()
    )
    if missing_artifact_paths:
        findings.append(f"Release manifest artifact paths are missing: {missing_artifact_paths}")

    missing_dockerfiles = sorted(
        image.dockerfile
        for image in RELEASE_IMAGE_TARGETS
        if image.required and not (repo_root / image.dockerfile).is_file()
    )
    if missing_dockerfiles:
        findings.append(f"Release image Dockerfiles are missing: {missing_dockerfiles}")

    artifact_kind_set = {artifact.kind for artifact in REQUIRED_RELEASE_ARTIFACTS}
    required_kinds = {
        "api_contract",
        "database_contract",
        "security_contract",
        "observability_contract",
        "operations_contract",
        "deployment_config",
        "infrastructure_plan",
        "runbook",
        "ci_workflow",
    }
    missing_kinds = sorted(required_kinds - artifact_kind_set)
    if missing_kinds:
        findings.append(f"Release manifest missing artifact kinds: {missing_kinds}")

    required_gates = {
        "backend_tests",
        "frontend_e2e",
        "docker_build",
        "production_readiness",
        "release_manifest_contract",
        "release_smoke_contract",
        "release_evidence_workflow_contract",
        "release_manifest_verifier_contract",
    }
    missing_gates = sorted(required_gates - set(REQUIRED_QUALITY_GATES))
    if missing_gates:
        findings.append(f"Release manifest missing quality gates: {missing_gates}")

    contract = build_release_manifest_contract()
    if contract["schema_version"] != RELEASE_MANIFEST_CONTRACT_VERSION:
        findings.append("Release manifest contract schema version is inconsistent.")
    if "sha256" not in contract["operator_command"]:
        findings.append("Release manifest command should be provenance-oriented.")

    return tuple(findings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify the ForgeML release manifest contract."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the checked-in release manifest contract.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate the checked-in release manifest contract.",
    )
    args = parser.parse_args(argv)

    if args.write:
        write_release_manifest_contract(args.output)
        print(f"Wrote release manifest contract: {args.output}")
        return 0

    passed, detail = check_release_manifest_contract(args.output)
    print(("PASS " if passed else "FAIL ") + detail)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
