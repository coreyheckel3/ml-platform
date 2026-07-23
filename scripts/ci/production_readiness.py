from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BANNED_TOKENS = ("TO" + "DO", "T" + "BD", "FIX" + "ME", "place" + "holder")
SCAN_ROOTS = (
    "backend/src",
    "backend/tests",
    "frontend/src",
    "frontend/tests",
    "infra",
    "load",
    "ml",
    "examples",
    "scripts",
    "docs",
    "README.md",
)
REQUIRED_FILES = (
    ".github/workflows/ci.yml",
    ".github/workflows/terraform-plan.yml",
    "docs/runbooks/backup-restore.md",
    "docs/runbooks/incident-response.md",
    "docs/runbooks/production-readiness.md",
    "docs/security/threat-model.md",
    "infra/compose/docker-compose.yml",
    "infra/observability/prometheus/prometheus.yml",
    "infra/observability/grafana/provisioning/datasources/prometheus.yml",
    "infra/observability/grafana/provisioning/dashboards/dashboards.yml",
    "infra/observability/grafana/dashboards/forgeml-platform.json",
    "infra/terraform/environments/staging/main.tf",
    "infra/terraform/environments/staging/outputs.tf",
    "infra/terraform/environments/staging/variables.tf",
    "infra/terraform/environments/staging/versions.tf",
    "load/k6/api_smoke.js",
    "backend/src/forgeml/modules/training/infrastructure/execution.py",
    "backend/tests/unit/training/test_training_execution.py",
    "ml/examples/fraud_detection/train.py",
    "ml/examples/movie_recommendation/train.py",
    "ml/examples/semantic_search/build_index.py",
    "scripts/examples/run_local_training.py",
    "scripts/ops/backup_postgres.sh",
    "scripts/ops/restore_postgres.sh",
    "backend/tests/unit/ml/test_example_training_pipelines.py",
)


@dataclass(frozen=True)
class ReadinessCheck:
    name: str
    passed: bool
    detail: str


def run_checks(repo_root: Path = REPO_ROOT) -> list[ReadinessCheck]:
    return [
        check_required_files(repo_root),
        check_marker_scan(repo_root),
        check_grafana_dashboard(repo_root),
        check_observability_compose_wiring(repo_root),
        check_ops_scripts(repo_root),
        check_load_test_contract(repo_root),
        check_staging_terraform(repo_root),
        check_example_training_contract(repo_root),
        check_training_execution_contract(repo_root),
    ]


def check_required_files(repo_root: Path) -> ReadinessCheck:
    missing = [path for path in REQUIRED_FILES if not (repo_root / path).is_file()]
    return ReadinessCheck(
        name="required production assets",
        passed=not missing,
        detail="all required assets exist" if not missing else f"missing: {', '.join(missing)}",
    )


def check_marker_scan(repo_root: Path) -> ReadinessCheck:
    findings: list[str] = []
    for root in SCAN_ROOTS:
        path = repo_root / root
        if path.is_file():
            _scan_file(path, repo_root, findings)
            continue
        for file_path in path.rglob("*"):
            if file_path.is_file():
                _scan_file(file_path, repo_root, findings)

    return ReadinessCheck(
        name="source hygiene marker scan",
        passed=not findings,
        detail="no banned markers found" if not findings else "; ".join(findings[:10]),
    )


def check_grafana_dashboard(repo_root: Path) -> ReadinessCheck:
    dashboard_path = repo_root / "infra/observability/grafana/dashboards/forgeml-platform.json"
    dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))
    panels = dashboard.get("panels", [])
    titles = {panel.get("title") for panel in panels}
    required_titles = {
        "API Request Rate",
        "API Latency P95",
        "API Error Rate",
        "Rate Limited Requests",
    }
    missing_titles = sorted(required_titles - titles)
    return ReadinessCheck(
        name="grafana dashboard contract",
        passed=not missing_titles and dashboard.get("uid") == "forgeml-platform-health",
        detail=(
            "dashboard has required panels"
            if not missing_titles
            else f"missing panels: {', '.join(missing_titles)}"
        ),
    )


def check_observability_compose_wiring(repo_root: Path) -> ReadinessCheck:
    compose = (repo_root / "infra/compose/docker-compose.yml").read_text(encoding="utf-8")
    required_fragments = (
        "../observability/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro",
        "../observability/grafana/provisioning:/etc/grafana/provisioning:ro",
        "../observability/grafana/dashboards:/var/lib/grafana/dashboards:ro",
        "grafana-data:",
        "postgres-data:",
    )
    missing = [fragment for fragment in required_fragments if fragment not in compose]
    return ReadinessCheck(
        name="compose observability wiring",
        passed=not missing,
        detail="compose mounts observability assets" if not missing else f"missing: {missing}",
    )


def check_ops_scripts(repo_root: Path) -> ReadinessCheck:
    scripts = [
        repo_root / "scripts/ops/backup_postgres.sh",
        repo_root / "scripts/ops/restore_postgres.sh",
    ]
    invalid = [
        script.relative_to(repo_root).as_posix()
        for script in scripts
        if "set -euo pipefail" not in script.read_text(encoding="utf-8")
    ]
    return ReadinessCheck(
        name="ops script safety flags",
        passed=not invalid,
        detail="ops scripts use strict shell mode" if not invalid else f"invalid: {invalid}",
    )


def check_load_test_contract(repo_root: Path) -> ReadinessCheck:
    load_test = (repo_root / "load/k6/api_smoke.js").read_text(encoding="utf-8")
    required_fragments = ("http_req_failed", "http_req_duration", "/health/ready", "/metrics")
    missing = [fragment for fragment in required_fragments if fragment not in load_test]
    return ReadinessCheck(
        name="load test contract",
        passed=not missing,
        detail="load smoke test has thresholds" if not missing else f"missing: {missing}",
    )


def check_staging_terraform(repo_root: Path) -> ReadinessCheck:
    staging_dir = repo_root / "infra/terraform/environments/staging"
    expected = {"main.tf", "outputs.tf", "variables.tf", "versions.tf"}
    found = {path.name for path in staging_dir.iterdir() if path.is_file()}
    missing = sorted(expected - found)
    main_tf = (staging_dir / "main.tf").read_text(encoding="utf-8")
    uses_variables = "var.project_name" in main_tf and "var.availability_zones" in main_tf
    return ReadinessCheck(
        name="staging terraform contract",
        passed=not missing and uses_variables,
        detail=(
            "staging terraform is variable driven"
            if not missing and uses_variables
            else f"missing={missing}, uses_variables={uses_variables}"
        ),
    )


def check_example_training_contract(repo_root: Path) -> ReadinessCheck:
    trainer_paths = [
        "ml/examples/fraud_detection/train.py",
        "ml/examples/movie_recommendation/train.py",
        "ml/examples/semantic_search/build_index.py",
    ]
    paths = [
        *trainer_paths,
        "scripts/examples/run_local_training.py",
    ]
    missing = [path for path in paths if not (repo_root / path).is_file()]
    if missing:
        return ReadinessCheck(
            name="example training contract",
            passed=False,
            detail=f"missing: {', '.join(missing)}",
        )

    trainer_sources = [
        (path, (repo_root / path).read_text(encoding="utf-8"))
        for path in trainer_paths
    ]
    orchestrator = (repo_root / "scripts/examples/run_local_training.py").read_text(
        encoding="utf-8"
    )
    required_slugs = {"fraud-detection", "movie-recommendation", "semantic-search"}
    missing_slugs = sorted(slug for slug in required_slugs if slug not in orchestrator)
    missing_schema = [
        path
        for path, source in trainer_sources
        if "forgeml.example_model_artifact.v1" not in source
    ]
    has_manifest_output = "training-summary.json" in orchestrator
    has_project_summary_output = all("summary.json" in source for _path, source in trainer_sources)
    passed = (
        not missing_slugs
        and not missing_schema
        and has_manifest_output
        and has_project_summary_output
    )
    return ReadinessCheck(
        name="example training contract",
        passed=passed,
        detail=(
            "example trainers and orchestrator expose versioned artifacts"
            if passed
            else (
                f"missing_slugs={missing_slugs}, "
                f"missing_schema={missing_schema}, "
                f"has_manifest_output={has_manifest_output}, "
                f"has_project_summary_output={has_project_summary_output}"
            )
        ),
    )


def check_training_execution_contract(repo_root: Path) -> ReadinessCheck:
    service_source = (
        repo_root / "backend/src/forgeml/modules/training/application/services.py"
    ).read_text(encoding="utf-8")
    config_source = (repo_root / "backend/src/forgeml/platform/config.py").read_text(
        encoding="utf-8"
    )
    routes_source = (
        repo_root / "backend/src/forgeml/modules/training/api/routes.py"
    ).read_text(encoding="utf-8")
    runner_source = (
        repo_root / "backend/src/forgeml/modules/training/infrastructure/execution.py"
    ).read_text(encoding="utf-8")
    bootstrap_source = (repo_root / "scripts/examples/bootstrap_examples.py").read_text(
        encoding="utf-8"
    )
    required_fragments = {
        "execute_training_run": service_source,
        "TrainingJobRunner": service_source,
        "forgeml.training_execution_result.v1": service_source,
        "EXAMPLE_PROJECT_SLUG_PARAMETER": runner_source,
        "LocalExampleTrainingRunner": runner_source,
        "FORGEML_LOCAL_TRAINING_ARTIFACT_ROOT": config_source,
        "runner=LocalExampleTrainingRunner": routes_source,
        "build_training_execution_report": bootstrap_source,
    }
    missing = [
        fragment for fragment, source in required_fragments.items() if fragment not in source
    ]
    return ReadinessCheck(
        name="training execution contract",
        passed=not missing,
        detail=(
            "training execution runner is wired behind application contracts"
            if not missing
            else f"missing: {missing}"
        ),
    )


def _scan_file(path: Path, repo_root: Path, findings: list[str]) -> None:
    if path.suffix in {".png", ".jpg", ".jpeg", ".gif", ".ico"}:
        return
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return
    for line_number, line in enumerate(text.splitlines(), start=1):
        if any(token in line for token in BANNED_TOKENS):
            findings.append(f"{path.relative_to(repo_root)}:{line_number}")


def main() -> int:
    checks = run_checks()
    for check in checks:
        status = "PASS" if check.passed else "FAIL"
        print(f"{status} {check.name}: {check.detail}")
    return 0 if all(check.passed for check in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
