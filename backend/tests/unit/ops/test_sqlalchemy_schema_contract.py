import json
from pathlib import Path

from scripts.ci.check_sqlalchemy_schema_contract import (
    SCHEMA_CONTRACT_SCHEMA_VERSION,
    build_schema_contract,
    check_schema_contract,
    serialize_schema_contract,
    validate_schema_metadata,
    write_schema_contract,
)
from sqlalchemy import Column, ForeignKey, Integer, MetaData, String, Table


def test_schema_contract_extracts_checked_in_metadata() -> None:
    contract = build_schema_contract()
    table_names = {table["name"] for table in contract["tables"]}

    assert contract["summary"]["table_count"] >= 38
    assert contract["summary"]["column_count"] >= 250
    assert {
        "projects",
        "datasets",
        "training_runs",
        "model_versions",
        "deployment_revisions",
        "inference_request_logs",
        "drift_reports",
        "retraining_runs",
        "training_run_logs",
    }.issubset(table_names)
    assert validate_schema_metadata() == ()


def test_schema_contract_write_and_check_round_trip(tmp_path: Path) -> None:
    contract_path = tmp_path / "sqlalchemy-schema.v1.json"

    write_schema_contract(contract_path)

    passed, detail = check_schema_contract(contract_path)
    assert passed
    assert str(contract_path) in detail


def test_schema_contract_detects_stale_contract(tmp_path: Path) -> None:
    contract_path = tmp_path / "sqlalchemy-schema.v1.json"
    contract_path.write_text("{}", encoding="utf-8")

    passed, detail = check_schema_contract(contract_path)

    assert not passed
    assert "stale" in detail


def test_schema_contract_detects_missing_required_tables() -> None:
    metadata = MetaData()
    Table("projects", metadata, Column("id", Integer, primary_key=True))

    findings = validate_schema_metadata(metadata, required_tables=frozenset({"projects", "users"}))

    assert any("Missing required SQLAlchemy tables: users" in finding for finding in findings)


def test_schema_contract_detects_table_without_primary_key() -> None:
    metadata = MetaData()
    Table("projects", metadata, Column("name", String(120), nullable=False))

    findings = validate_schema_metadata(metadata, required_tables=frozenset({"projects"}))

    assert any("projects does not define a primary key" in finding for finding in findings)


def test_schema_contract_detects_non_snake_case_names() -> None:
    metadata = MetaData()
    Table("ProjectRecords", metadata, Column("OwnerUserID", Integer, primary_key=True))

    findings = validate_schema_metadata(
        metadata,
        required_tables=frozenset({"ProjectRecords"}),
    )

    assert any("ProjectRecords is not snake_case" in finding for finding in findings)
    assert any("ProjectRecords.OwnerUserID is not snake_case" in finding for finding in findings)


def test_schema_contract_detects_unindexed_foreign_key() -> None:
    metadata = MetaData()
    Table("projects", metadata, Column("id", Integer, primary_key=True))
    Table(
        "training_runs",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("project_id", Integer, ForeignKey("projects.id")),
    )

    findings = validate_schema_metadata(
        metadata,
        required_tables=frozenset({"projects", "training_runs"}),
    )

    assert any(
        "training_runs.project_id has a foreign key but no index flag" in finding
        for finding in findings
    )


def test_checked_in_schema_contract_matches_source() -> None:
    passed, detail = check_schema_contract(Path("contracts/database/sqlalchemy-schema.v1.json"))

    assert passed, detail


def test_schema_contract_serialization_is_deterministic() -> None:
    contract = build_schema_contract()

    assert serialize_schema_contract(contract) == serialize_schema_contract(contract)


def test_schema_contract_shape() -> None:
    parsed = json.loads(serialize_schema_contract(build_schema_contract()))
    projects_table = next(table for table in parsed["tables"] if table["name"] == "projects")
    training_runs_table = next(
        table for table in parsed["tables"] if table["name"] == "training_runs"
    )
    project_columns = {column["name"]: column for column in projects_table["columns"]}
    training_run_columns = {
        column["name"]: column for column in training_runs_table["columns"]
    }

    assert parsed["schema_version"] == SCHEMA_CONTRACT_SCHEMA_VERSION
    assert parsed["dialect"] == "postgresql"
    assert parsed["summary"]["table_count"] == len(parsed["tables"])
    assert projects_table["primary_key"] == ["id"]
    assert project_columns["id"]["primary_key"]
    assert training_run_columns["project_id"]["foreign_keys"] == ["projects.id"]
