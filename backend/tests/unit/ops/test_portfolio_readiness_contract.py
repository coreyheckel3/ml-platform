import json
from pathlib import Path

from scripts.ci.check_portfolio_readiness_contract import (
    build_portfolio_readiness_contract,
    check_portfolio_readiness_contract,
    serialize_portfolio_readiness_contract,
    validate_portfolio_readiness_definition,
    write_portfolio_readiness_contract,
)


def test_portfolio_readiness_definition_validates_required_assets() -> None:
    assert validate_portfolio_readiness_definition(Path(".")) == ()


def test_portfolio_readiness_contract_write_and_check_round_trip(
    tmp_path: Path,
) -> None:
    contract_path = tmp_path / "portfolio-readiness.v1.json"
    ci_path = tmp_path / "ci.yml"
    ci_path.write_text(
        "python scripts/ci/check_portfolio_readiness_contract.py",
        encoding="utf-8",
    )

    write_portfolio_readiness_contract(contract_path)

    passed, detail = check_portfolio_readiness_contract(contract_path, ci_path=ci_path)
    assert passed
    assert str(contract_path) in detail


def test_portfolio_readiness_contract_detects_stale_contract(
    tmp_path: Path,
) -> None:
    contract_path = tmp_path / "portfolio-readiness.v1.json"
    ci_path = tmp_path / "ci.yml"
    contract_path.write_text("{}", encoding="utf-8")
    ci_path.write_text(
        "python scripts/ci/check_portfolio_readiness_contract.py",
        encoding="utf-8",
    )

    passed, detail = check_portfolio_readiness_contract(contract_path, ci_path=ci_path)

    assert not passed
    assert "stale" in detail


def test_portfolio_readiness_contract_requires_ci_wiring(tmp_path: Path) -> None:
    contract_path = tmp_path / "portfolio-readiness.v1.json"
    ci_path = tmp_path / "ci.yml"
    write_portfolio_readiness_contract(contract_path)
    ci_path.write_text("pytest backend/tests", encoding="utf-8")

    passed, detail = check_portfolio_readiness_contract(contract_path, ci_path=ci_path)

    assert not passed
    assert "not wired into CI" in detail


def test_checked_in_portfolio_readiness_contract_matches_source() -> None:
    passed, detail = check_portfolio_readiness_contract(
        Path("contracts/ops/portfolio-readiness.v1.json")
    )

    assert passed, detail


def test_portfolio_readiness_contract_shape() -> None:
    parsed = json.loads(
        serialize_portfolio_readiness_contract(build_portfolio_readiness_contract())
    )
    asset_paths = {asset["path"] for asset in parsed["reviewer_assets"]}

    assert parsed["schema_version"] == "forgeml.portfolio_readiness_contract.v1"
    assert "docs/portfolio/reviewer-guide.md" in asset_paths
    assert "docs/portfolio/resume-bullets.md" in asset_paths
    assert "docs/portfolio/evidence-map.md" in asset_paths
    assert "docs/portfolio/architecture-diagrams.md" in asset_paths
    assert "docs/portfolio/screenshot-catalog.md" in asset_paths
    assert "mlops_release_governance" in parsed["portfolio_claims"]
    assert "browser_verified_demo" in parsed["portfolio_claims"]
    assert "python scripts/ci/check_portfolio_readiness_contract.py" in parsed[
        "quality_gates"
    ]
