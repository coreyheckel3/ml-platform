import json
from pathlib import Path

import pytest
from scripts.dev.demo_reset import (
    DEMO_RESET_SCHEMA_VERSION,
    DemoResetError,
    DemoResetTarget,
    build_demo_reset_plan,
    reset_demo_environment,
    safe_reset_targets,
    serialize_demo_reset_report,
    write_demo_reset_report,
)


def test_demo_reset_plan_is_repo_scoped(tmp_path: Path) -> None:
    (tmp_path / ".forgeml/demo").mkdir(parents=True)

    plan = build_demo_reset_plan(repo_root=tmp_path)
    targets = {target["code"]: target for target in plan["targets"]}

    assert plan["schema_version"] == DEMO_RESET_SCHEMA_VERSION
    assert plan["safety_policy"]["docker_volumes_removed"] is False
    assert plan["safety_policy"]["database_rows_removed"] is False
    assert targets["demo_state"]["exists"] is True
    assert targets["release_manifest"]["path"] == "dist/release/forgeml-release-manifest.json"
    assert "make demo-stack-fresh" in plan["reviewer_next_commands"]


def test_demo_reset_dry_run_keeps_outputs(tmp_path: Path) -> None:
    state_file = tmp_path / ".forgeml/demo/demo-data-refresh.json"
    state_file.parent.mkdir(parents=True)
    state_file.write_text("{}", encoding="utf-8")

    report = reset_demo_environment(
        repo_root=tmp_path,
        targets=safe_reset_targets(include_screenshots=False),
        dry_run=True,
    )

    assert report["dry_run"] is True
    assert state_file.exists()
    assert report["removed"] == []
    assert report["skipped"][0]["reason"] == "dry_run"


def test_demo_reset_removes_only_declared_targets(tmp_path: Path) -> None:
    state_file = tmp_path / ".forgeml/demo/demo-stack-summary.json"
    manifest_file = tmp_path / "dist/release/forgeml-release-manifest.json"
    untouched_file = tmp_path / "README.md"
    state_file.parent.mkdir(parents=True)
    manifest_file.parent.mkdir(parents=True)
    state_file.write_text("{}", encoding="utf-8")
    manifest_file.write_text("{}", encoding="utf-8")
    untouched_file.write_text("keep", encoding="utf-8")

    report = reset_demo_environment(
        repo_root=tmp_path,
        targets=safe_reset_targets(include_screenshots=False),
        dry_run=False,
    )

    assert sorted(item["code"] for item in report["removed"]) == [
        "demo_state",
        "release_manifest",
    ]
    assert not state_file.exists()
    assert not manifest_file.exists()
    assert untouched_file.exists()


def test_demo_reset_rejects_targets_outside_repo(tmp_path: Path) -> None:
    outside_repo = tmp_path.parent / "forgeml-outside-demo-state"

    with pytest.raises(DemoResetError, match="inside the repository"):
        reset_demo_environment(
            repo_root=tmp_path,
            targets=(
                DemoResetTarget(
                    code="outside",
                    description="outside path",
                    path=outside_repo,
                    kind="directory",
                ),
            ),
            dry_run=True,
        )


def test_demo_reset_report_write_round_trip(tmp_path: Path) -> None:
    report = {
        "schema_version": DEMO_RESET_SCHEMA_VERSION,
        "dry_run": True,
        "removed": [],
        "skipped": [],
    }
    output_path = tmp_path / "demo-reset-report.json"

    write_demo_reset_report(report, output_path)

    assert json.loads(output_path.read_text(encoding="utf-8")) == report
    assert serialize_demo_reset_report(report).endswith("\n")
