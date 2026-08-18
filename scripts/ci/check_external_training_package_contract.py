from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_SRC = REPO_ROOT / "backend/src"
for import_path in (REPO_ROOT, BACKEND_SRC):
    import_path_value = str(import_path)
    if import_path_value not in sys.path:
        sys.path.insert(0, import_path_value)

from forgeml.modules.training.infrastructure.external_package import (  # noqa: E402
    CONVERSATIONAL_MOVIE_RECOMMENDER_PROFILE_SLUG,
    EXTERNAL_TRAINING_PACKAGE_SCHEMA_VERSION,
    EXTERNAL_TRAINING_PROFILE_PARAMETER,
)

EXTERNAL_TRAINING_PACKAGE_CONTRACT_SCHEMA_VERSION = (
    "forgeml.external_training_package_contract.v1"
)
DEFAULT_OUTPUT_PATH = Path("contracts/training/external-package-runner.v1.json")
DEFAULT_CI_PATH = Path(".github/workflows/ci.yml")


def build_external_training_package_contract() -> dict[str, Any]:
    return {
        "schema_version": EXTERNAL_TRAINING_PACKAGE_CONTRACT_SCHEMA_VERSION,
        "runtime_schema_version": EXTERNAL_TRAINING_PACKAGE_SCHEMA_VERSION,
        "generated_from": [
            "forgeml.modules.training.infrastructure.external_package",
            "forgeml.modules.training.infrastructure.execution",
            "forgeml.modules.training.api.routes",
            "scripts.workers.run_training_worker",
            "frontend.src.modules.training_runs",
        ],
        "profile_selector": EXTERNAL_TRAINING_PROFILE_PARAMETER,
        "runner": {
            "class": "ExternalTrainingPackageRunner",
            "composite_runner": "CompositeTrainingJobRunner",
            "factory": "build_training_job_runner",
            "execution_policy": {
                "profile_allowlist": True,
                "shell": False,
                "repo_root_from_settings": True,
                "relative_data_paths_only": True,
                "fixed_output_root": "FORGEML_LOCAL_TRAINING_ARTIFACT_ROOT",
                "timeout_setting": "FORGEML_EXTERNAL_TRAINING_COMMAND_TIMEOUT_SECONDS",
            },
        },
        "profiles": [
            {
                "slug": CONVERSATIONAL_MOVIE_RECOMMENDER_PROFILE_SLUG,
                "package_name": "conversational-movie-recommender",
                "repo_root_setting": "FORGEML_EXTERNAL_TRAINING_MOVIE_RECOMMENDER_REPO_ROOT",
                "executable": ".venv/bin/movie-rec-build",
                "algorithms": ["movie-rec-svd", "movie-rec-two-tower"],
                "objective_metric_name": "ndcg_at_k",
                "default_data_dir": "data/sample",
                "artifact_mapping": {
                    "engine.joblib": "model",
                    "evaluation.json": "evaluation_report",
                    "*.joblib": "model_component",
                },
            }
        ],
        "api": {
            "endpoints": [
                {
                    "method": "GET",
                    "path": "/api/v1/training-runner-profiles",
                    "permission": "training_runs:read",
                },
                {
                    "method": "POST",
                    "path": "/api/v1/projects/{project_id}/training-runs",
                    "profile_selector_location": "hyperparameters",
                },
            ]
        },
        "frontend": {
            "page": "frontend/src/modules/training_runs/pages/TrainingRunsPage.tsx",
            "profile_panel": "External Package Profiles",
            "api_client": "listTrainingRunnerProfiles",
        },
        "quality_gates": [
            "python scripts/ci/check_external_training_package_contract.py",
            "backend/tests/unit/training/test_external_package_training.py",
            "backend/tests/unit/ops/test_external_training_package_contract.py",
            "backend/tests/api/test_training_api.py",
            "frontend/src/modules/training_runs/pages/TrainingRunsPage.test.tsx",
        ],
    }


def serialize_external_training_package_contract(contract: dict[str, Any]) -> str:
    return json.dumps(contract, indent=2, sort_keys=True) + "\n"


def write_external_training_package_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        serialize_external_training_package_contract(
            build_external_training_package_contract()
        ),
        encoding="utf-8",
    )


def check_external_training_package_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    *,
    ci_path: Path = DEFAULT_CI_PATH,
    repo_root: Path = REPO_ROOT,
) -> tuple[bool, str]:
    findings = list(validate_external_training_package_definition(repo_root))
    if not output_path.is_file():
        findings.append(f"External training package contract does not exist: {output_path}")
    else:
        expected = serialize_external_training_package_contract(
            build_external_training_package_contract()
        )
        actual = output_path.read_text(encoding="utf-8")
        if actual != expected:
            findings.append(f"External training package contract is stale: {output_path}")

    if not ci_path.is_file():
        findings.append(f"CI workflow does not exist: {ci_path}")
    else:
        ci_source = ci_path.read_text(encoding="utf-8")
        if "python scripts/ci/check_external_training_package_contract.py" not in ci_source:
            findings.append("External training package contract checker is not wired into CI.")

    if findings:
        return False, "External training package contract violations: " + "; ".join(findings)
    return True, f"External training package contract is current: {output_path}"


def validate_external_training_package_definition(
    repo_root: Path = REPO_ROOT,
) -> tuple[str, ...]:
    required_files = [
        "backend/src/forgeml/modules/training/infrastructure/external_package.py",
        "backend/src/forgeml/modules/training/infrastructure/execution.py",
        "backend/src/forgeml/modules/training/api/routes.py",
        "backend/src/forgeml/modules/training/api/schemas.py",
        "backend/src/forgeml/platform/config.py",
        "backend/src/forgeml/platform/config_policy.py",
        "scripts/workers/run_training_worker.py",
        "frontend/src/modules/training_runs/api/trainingRuns.ts",
        "frontend/src/modules/training_runs/pages/TrainingRunsPage.tsx",
        "frontend/src/modules/training_runs/pages/TrainingRunsPage.test.tsx",
        "frontend/tests/e2e/fixtures/forgemlApiMock.ts",
        "backend/tests/unit/training/test_external_package_training.py",
        "backend/tests/unit/ops/test_external_training_package_contract.py",
        "backend/tests/api/test_training_api.py",
        "docs/runbooks/demo-readiness.md",
        "docs/architecture-walkthrough.md",
        "outputs/forgeml/docs/05-sprint-breakdown.md",
    ]
    findings = [
        f"Missing external training package source file: {path}"
        for path in required_files
        if not (repo_root / path).is_file()
    ]
    if findings:
        return tuple(findings)

    sources = {path: (repo_root / path).read_text(encoding="utf-8") for path in required_files}
    required_fragments = [
        (
            "ExternalTrainingPackageRunner",
            sources["backend/src/forgeml/modules/training/infrastructure/external_package.py"],
        ),
        (
            "subprocess.run",
            sources["backend/src/forgeml/modules/training/infrastructure/external_package.py"],
        ),
        (
            "shell=False",
            sources["backend/src/forgeml/modules/training/infrastructure/external_package.py"],
        ),
        (
            "EXTERNAL_TRAINING_PROFILE_PARAMETER",
            sources["backend/src/forgeml/modules/training/infrastructure/external_package.py"],
        ),
        (
            "conversational_movie_recommender_profile",
            sources["backend/src/forgeml/modules/training/infrastructure/external_package.py"],
        ),
        (
            "CompositeTrainingJobRunner",
            sources["backend/src/forgeml/modules/training/infrastructure/execution.py"],
        ),
        (
            "build_training_job_runner",
            sources["backend/src/forgeml/modules/training/infrastructure/execution.py"],
        ),
        (
            "external_training_profile_catalog",
            sources["backend/src/forgeml/modules/training/infrastructure/execution.py"],
        ),
        (
            "runner=build_training_job_runner",
            sources["backend/src/forgeml/modules/training/api/routes.py"],
        ),
        (
            "/training-runner-profiles",
            sources["backend/src/forgeml/modules/training/api/routes.py"],
        ),
        (
            "TrainingRunnerProfileResponse",
            sources["backend/src/forgeml/modules/training/api/schemas.py"],
        ),
        (
            "FORGEML_EXTERNAL_TRAINING_PROFILES_ENABLED",
            sources["backend/src/forgeml/platform/config.py"],
        ),
        (
            "FORGEML_EXTERNAL_TRAINING_MOVIE_RECOMMENDER_REPO_ROOT",
            sources["backend/src/forgeml/platform/config.py"],
        ),
        (
            "external_training_profiles_disabled",
            sources["backend/src/forgeml/platform/config_policy.py"],
        ),
        (
            "runner=build_training_job_runner",
            sources["scripts/workers/run_training_worker.py"],
        ),
        (
            "listTrainingRunnerProfiles",
            sources["frontend/src/modules/training_runs/api/trainingRuns.ts"],
        ),
        (
            "External Package Profiles",
            sources["frontend/src/modules/training_runs/pages/TrainingRunsPage.tsx"],
        ),
        ("Use profile", sources["frontend/src/modules/training_runs/pages/TrainingRunsPage.tsx"]),
        (
            "test_external_training_package_runner_executes_profile",
            sources["backend/tests/unit/training/test_external_package_training.py"],
        ),
        (
            "test_checked_in_external_training_package_contract_matches_source",
            sources["backend/tests/unit/ops/test_external_training_package_contract.py"],
        ),
        (
            "test_training_runner_profile_route_exposes_external_package_profile",
            sources["backend/tests/api/test_training_api.py"],
        ),
        ("conversational-movie-recommender", sources["docs/runbooks/demo-readiness.md"]),
        (
            "Sprint 66: External Training Package Adapter",
            sources["outputs/forgeml/docs/05-sprint-breakdown.md"],
        ),
    ]
    missing_fragments = sorted(
        fragment
        for fragment, source in required_fragments
        if fragment not in source
    )
    if missing_fragments:
        findings.append(f"Missing external training package fragments: {missing_fragments}")

    contract = build_external_training_package_contract()
    if contract["runtime_schema_version"] != EXTERNAL_TRAINING_PACKAGE_SCHEMA_VERSION:
        findings.append("External training package runtime schema version is inconsistent.")
    if contract["profile_selector"] != EXTERNAL_TRAINING_PROFILE_PARAMETER:
        findings.append("External training package profile selector is inconsistent.")

    return tuple(findings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify the ForgeML external training package adapter contract."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the checked-in external training package contract.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate the checked-in external training package contract.",
    )
    args = parser.parse_args(argv)

    if args.write:
        write_external_training_package_contract(args.output)
        print(f"Wrote external training package contract: {args.output}")
        return 0

    passed, detail = check_external_training_package_contract(args.output)
    print(("PASS " if passed else "FAIL ") + detail)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
