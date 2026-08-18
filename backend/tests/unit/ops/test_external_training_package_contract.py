import json
from pathlib import Path

from scripts.ci.check_external_training_package_contract import (
    build_external_training_package_contract,
    check_external_training_package_contract,
    serialize_external_training_package_contract,
    validate_external_training_package_definition,
    write_external_training_package_contract,
)


def test_external_training_package_definition_validates_required_assets() -> None:
    assert validate_external_training_package_definition(Path(".")) == ()


def test_external_training_package_contract_write_and_check_round_trip(
    tmp_path: Path,
) -> None:
    contract_path = tmp_path / "external-package-runner.v1.json"
    ci_path = tmp_path / "ci.yml"
    ci_path.write_text(
        "python scripts/ci/check_external_training_package_contract.py",
        encoding="utf-8",
    )

    write_external_training_package_contract(contract_path)

    passed, detail = check_external_training_package_contract(
        contract_path,
        ci_path=ci_path,
    )

    assert passed
    assert str(contract_path) in detail


def test_external_training_package_contract_detects_stale_contract(
    tmp_path: Path,
) -> None:
    contract_path = tmp_path / "external-package-runner.v1.json"
    ci_path = tmp_path / "ci.yml"
    contract_path.write_text("{}", encoding="utf-8")
    ci_path.write_text(
        "python scripts/ci/check_external_training_package_contract.py",
        encoding="utf-8",
    )

    passed, detail = check_external_training_package_contract(
        contract_path,
        ci_path=ci_path,
    )

    assert not passed
    assert "stale" in detail


def test_external_training_package_contract_requires_ci_wiring(
    tmp_path: Path,
) -> None:
    contract_path = tmp_path / "external-package-runner.v1.json"
    ci_path = tmp_path / "ci.yml"
    write_external_training_package_contract(contract_path)
    ci_path.write_text("pytest backend/tests", encoding="utf-8")

    passed, detail = check_external_training_package_contract(
        contract_path,
        ci_path=ci_path,
    )

    assert not passed
    assert "not wired into CI" in detail


def test_checked_in_external_training_package_contract_matches_source() -> None:
    passed, detail = check_external_training_package_contract(
        Path("contracts/training/external-package-runner.v1.json")
    )

    assert passed, detail


def test_external_training_package_contract_shape() -> None:
    parsed = json.loads(
        serialize_external_training_package_contract(
            build_external_training_package_contract()
        )
    )
    profile = parsed["profiles"][0]

    assert parsed["schema_version"] == "forgeml.external_training_package_contract.v1"
    assert parsed["runtime_schema_version"] == "forgeml.external_training_package.v1"
    assert parsed["profile_selector"] == "forgeml.external_training_profile"
    assert parsed["runner"]["execution_policy"]["shell"] is False
    assert profile["slug"] == "conversational-movie-recommender"
    assert profile["executable"] == ".venv/bin/movie-rec-build"
    assert "movie-rec-svd" in profile["algorithms"]
    assert "movie-rec-two-tower" in profile["algorithms"]
    assert "backend/tests/unit/ops/test_external_training_package_contract.py" in parsed[
        "quality_gates"
    ]
