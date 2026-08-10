import json
from pathlib import Path

from scripts.ci.check_alembic_migration_contract import (
    MIGRATION_CONTRACT_SCHEMA_VERSION,
    build_migration_contract,
    check_migration_contract,
    extract_migration_revisions,
    serialize_migration_contract,
    validate_migration_graph,
    write_migration_contract,
)


def test_migration_contract_extracts_checked_in_topology() -> None:
    migrations = extract_migration_revisions(Path("backend/alembic/versions"))
    contract = build_migration_contract()

    assert len(migrations) >= 14
    assert contract["summary"]["base_revision"] == "202607180001"
    assert contract["summary"]["head_revision"] == "202607190015"
    assert contract["summary"]["head_count"] == 1
    assert contract["summary"]["base_count"] == 1
    assert validate_migration_graph(migrations) == ()


def test_migration_contract_write_and_check_round_trip(tmp_path: Path) -> None:
    contract_path = tmp_path / "alembic-migrations.v1.json"

    write_migration_contract(contract_path)

    passed, detail = check_migration_contract(contract_path)
    assert passed
    assert str(contract_path) in detail


def test_migration_contract_detects_stale_contract(tmp_path: Path) -> None:
    contract_path = tmp_path / "alembic-migrations.v1.json"
    contract_path.write_text("{}", encoding="utf-8")

    passed, detail = check_migration_contract(contract_path)

    assert not passed
    assert "stale" in detail


def test_migration_contract_detects_unknown_down_revision(tmp_path: Path) -> None:
    _write_migration(tmp_path / "001_base.py", "001", None)
    _write_migration(tmp_path / "002_child.py", "002", "missing")

    findings = validate_migration_graph(extract_migration_revisions(tmp_path))

    assert any("unknown down_revision missing" in finding for finding in findings)


def test_migration_contract_detects_duplicate_revision(tmp_path: Path) -> None:
    _write_migration(tmp_path / "001_base.py", "001", None)
    _write_migration(tmp_path / "001_duplicate.py", "001", None)

    findings = validate_migration_graph(extract_migration_revisions(tmp_path))

    assert any("Duplicate Alembic revision: 001" in finding for finding in findings)


def test_migration_contract_detects_multiple_heads(tmp_path: Path) -> None:
    _write_migration(tmp_path / "001_base.py", "001", None)
    _write_migration(tmp_path / "002_left.py", "002", "001")
    _write_migration(tmp_path / "003_right.py", "003", "001")

    findings = validate_migration_graph(extract_migration_revisions(tmp_path))

    assert any(
        "Expected exactly one Alembic head revision, found 2" in finding
        for finding in findings
    )


def test_migration_contract_requires_downgrade(tmp_path: Path) -> None:
    (tmp_path / "001_base.py").write_text(
        'revision = "001"\n'
        "down_revision = None\n"
        "\n"
        "def upgrade() -> None:\n"
        "    pass\n",
        encoding="utf-8",
    )

    findings = validate_migration_graph(extract_migration_revisions(tmp_path))

    assert any("does not define downgrade()" in finding for finding in findings)


def test_checked_in_migration_contract_matches_source() -> None:
    passed, detail = check_migration_contract(
        Path("contracts/database/alembic-migrations.v1.json")
    )

    assert passed, detail


def test_migration_contract_serialization_is_deterministic() -> None:
    contract = build_migration_contract()

    assert serialize_migration_contract(contract) == serialize_migration_contract(contract)


def test_migration_contract_shape() -> None:
    parsed = json.loads(serialize_migration_contract(build_migration_contract()))

    assert parsed["schema_version"] == MIGRATION_CONTRACT_SCHEMA_VERSION
    assert parsed["summary"]["migration_count"] == len(parsed["migrations"])
    assert parsed["heads"] == [parsed["summary"]["head_revision"]]
    assert parsed["bases"] == [parsed["summary"]["base_revision"]]
    assert parsed["linearized_revision_order"][0] == parsed["summary"]["base_revision"]
    assert parsed["linearized_revision_order"][-1] == parsed["summary"]["head_revision"]


def _write_migration(path: Path, revision: str, down_revision: str | None) -> None:
    down_revision_value = "None" if down_revision is None else f'"{down_revision}"'
    path.write_text(
        f'revision: str = "{revision}"\n'
        f"down_revision: str | None = {down_revision_value}\n"
        "\n"
        "def upgrade() -> None:\n"
        "    pass\n"
        "\n"
        "def downgrade() -> None:\n"
        "    pass\n",
        encoding="utf-8",
    )
