import json
from pathlib import Path

from scripts.ci.check_release_evidence_workflow import (
    build_release_evidence_workflow_contract,
    check_release_evidence_workflow_contract,
    serialize_release_evidence_workflow_contract,
    validate_release_evidence_workflow,
    write_release_evidence_workflow_contract,
)

VALID_RELEASE_EVIDENCE_WORKFLOW = """
jobs:
  release-evidence:
    runs-on: ubuntu-latest
    needs: [backend, frontend, docker, production-readiness]
    if: ${{ github.event_name == 'push' && github.ref == 'refs/heads/main' }}
    steps:
      - name: Build release manifest
        run: >
          python scripts/ops/build_release_manifest.py
          --output dist/release/forgeml-release-manifest.json
          --git-sha "$GITHUB_SHA"
          --git-branch "$GITHUB_REF_NAME"
          --ci-run-url "$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID"
      - name: Upload release manifest
        uses: actions/upload-artifact@v7
        with:
          name: forgeml-release-manifest
          path: dist/release/forgeml-release-manifest.json
          if-no-files-found: error
"""


def test_release_evidence_workflow_validates_required_fragments() -> None:
    assert validate_release_evidence_workflow(VALID_RELEASE_EVIDENCE_WORKFLOW) == ()


def test_release_evidence_workflow_reports_missing_fragments() -> None:
    findings = validate_release_evidence_workflow("jobs: {}\n")

    assert findings
    assert "release-evidence" in findings[0]


def test_release_evidence_workflow_contract_write_and_check_round_trip(
    tmp_path: Path,
) -> None:
    contract_path = tmp_path / "release-evidence-workflow.v1.json"
    ci_path = tmp_path / "ci.yml"
    ci_path.write_text(VALID_RELEASE_EVIDENCE_WORKFLOW, encoding="utf-8")

    write_release_evidence_workflow_contract(contract_path)

    passed, detail = check_release_evidence_workflow_contract(contract_path, ci_path=ci_path)
    assert passed
    assert str(contract_path) in detail


def test_release_evidence_workflow_contract_detects_stale_contract(tmp_path: Path) -> None:
    contract_path = tmp_path / "release-evidence-workflow.v1.json"
    ci_path = tmp_path / "ci.yml"
    contract_path.write_text("{}", encoding="utf-8")
    ci_path.write_text(VALID_RELEASE_EVIDENCE_WORKFLOW, encoding="utf-8")

    passed, detail = check_release_evidence_workflow_contract(contract_path, ci_path=ci_path)

    assert not passed
    assert "stale" in detail


def test_checked_in_release_evidence_workflow_contract_matches_ci() -> None:
    passed, detail = check_release_evidence_workflow_contract(
        Path("contracts/ops/release-evidence-workflow.v1.json")
    )

    assert passed, detail


def test_release_evidence_workflow_contract_shape() -> None:
    parsed = json.loads(
        serialize_release_evidence_workflow_contract(
            build_release_evidence_workflow_contract()
        )
    )

    assert parsed["schema_version"] == "forgeml.release_evidence_workflow.v1"
    assert parsed["job_name"] == "release-evidence"
    assert parsed["artifact_name"] == "forgeml-release-manifest"
    assert parsed["manifest_path"] == "dist/release/forgeml-release-manifest.json"
    assert {"backend", "frontend", "docker", "production-readiness"}.issubset(
        parsed["required_needs"]
    )
