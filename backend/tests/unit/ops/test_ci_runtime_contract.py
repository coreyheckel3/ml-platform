import json
from pathlib import Path

from scripts.ci.check_ci_runtime_contract import (
    build_ci_runtime_contract,
    check_ci_runtime_contract,
    serialize_ci_runtime_contract,
    validate_ci_runtime_definition,
    validate_workflow_action_pins,
    write_ci_runtime_contract,
)

VALID_CI_WORKFLOW = """
jobs:
  backend:
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
      - name: Check CI runtime contract
        run: python scripts/ci/check_ci_runtime_contract.py
  frontend:
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-node@v7
      - uses: actions/setup-python@v7
  release-evidence:
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
      - uses: actions/upload-artifact@v7
"""


def test_ci_runtime_definition_validates_required_assets() -> None:
    assert validate_ci_runtime_definition(Path(".")) == ()


def test_workflow_action_pins_reject_retired_refs() -> None:
    findings = validate_workflow_action_pins(
        ".github/workflows/ci.yml",
        "steps:\n  - uses: actions/checkout@v4\n",
        [],
    )

    assert findings
    assert "retired action refs" in findings[0]


def test_ci_runtime_contract_write_and_check_round_trip(tmp_path: Path) -> None:
    contract_path = tmp_path / "ci-runtime.v1.json"
    ci_workflow = tmp_path / ".github/workflows/ci.yml"
    terraform_workflow = tmp_path / ".github/workflows/terraform-plan.yml"
    docs_path = tmp_path / "outputs/forgeml/docs/14-ci-cd-strategy.md"
    ci_workflow.parent.mkdir(parents=True)
    docs_path.parent.mkdir(parents=True)
    ci_workflow.write_text(VALID_CI_WORKFLOW, encoding="utf-8")
    terraform_workflow.write_text(
        "steps:\n  - uses: actions/checkout@v7\n  - uses: hashicorp/setup-terraform@v4\n",
        encoding="utf-8",
    )
    docs_path.write_text("CI runtime contract\n", encoding="utf-8")

    write_ci_runtime_contract(contract_path)

    passed, detail = check_ci_runtime_contract(contract_path, repo_root=tmp_path)
    assert passed
    assert str(contract_path) in detail


def test_ci_runtime_contract_detects_stale_contract(tmp_path: Path) -> None:
    contract_path = tmp_path / "ci-runtime.v1.json"
    contract_path.write_text("{}", encoding="utf-8")

    passed, detail = check_ci_runtime_contract(contract_path)

    assert not passed
    assert "stale" in detail


def test_checked_in_ci_runtime_contract_matches_source() -> None:
    passed, detail = check_ci_runtime_contract(Path("contracts/ops/ci-runtime.v1.json"))

    assert passed, detail


def test_ci_runtime_contract_shape() -> None:
    parsed = json.loads(serialize_ci_runtime_contract(build_ci_runtime_contract()))
    action_pins = {
        (pin["workflow"], pin["action"]): pin["required_ref"]
        for pin in parsed["action_pins"]
    }

    assert parsed["schema_version"] == "forgeml.ci_runtime_contract.v1"
    assert action_pins[(".github/workflows/ci.yml", "actions/checkout")] == "v7"
    assert action_pins[(".github/workflows/ci.yml", "actions/upload-artifact")] == "v7"
    assert action_pins[(".github/workflows/terraform-plan.yml", "hashicorp/setup-terraform")] == (
        "v4"
    )
    assert "actions/checkout@v4" in parsed["retired_action_refs"]
    assert "python scripts/ci/check_ci_runtime_contract.py" in parsed["quality_gates"]
