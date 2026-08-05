from __future__ import annotations

import argparse
import importlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import MetaData, Table
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import UniqueConstraint

from forgeml.platform.database.base import Base

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_PATH = Path("contracts/database/sqlalchemy-schema.v1.json")
SCHEMA_CONTRACT_SCHEMA_VERSION = "forgeml.sqlalchemy_schema.v1"
POSTGRES_DIALECT = postgresql.dialect()
SNAKE_CASE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
REQUIRED_TABLES = frozenset(
    {
        "alert_events",
        "alert_rules",
        "auth_refresh_sessions",
        "audit_log",
        "dataset_schemas",
        "dataset_validation_runs",
        "dataset_versions",
        "datasets",
        "deployment_events",
        "deployment_health_checks",
        "deployment_revisions",
        "deployments",
        "drift_feature_results",
        "drift_profiles",
        "drift_reports",
        "experiment_artifacts",
        "experiment_runs",
        "experiments",
        "feature_definitions",
        "feature_lineage",
        "feature_materializations",
        "feature_pipelines",
        "feature_sets",
        "inference_endpoints",
        "inference_metric_snapshots",
        "inference_request_logs",
        "model_approvals",
        "model_lineage",
        "model_versions",
        "organizations",
        "projects",
        "registered_models",
        "retraining_policies",
        "retraining_runs",
        "training_run_events",
        "training_run_logs",
        "training_runs",
        "users",
    }
)


def build_schema_contract(metadata: MetaData | None = None) -> dict[str, Any]:
    resolved_metadata = metadata or load_application_metadata()
    tables = [_table_contract(table) for table in _sorted_tables(resolved_metadata)]
    return {
        "schema_version": SCHEMA_CONTRACT_SCHEMA_VERSION,
        "generated_from": [
            "forgeml.platform.database.models",
            "forgeml.platform.database.base.Base.metadata",
        ],
        "dialect": "postgresql",
        "summary": {
            "table_count": len(tables),
            "column_count": sum(len(table["columns"]) for table in tables),
            "foreign_key_count": sum(
                len(column["foreign_keys"])
                for table in tables
                for column in table["columns"]
            ),
            "index_count": sum(len(table["indexes"]) for table in tables),
            "unique_constraint_count": sum(
                len(table["unique_constraints"]) for table in tables
            ),
        },
        "tables": tables,
    }


def validate_schema_metadata(
    metadata: MetaData | None = None,
    required_tables: frozenset[str] = REQUIRED_TABLES,
) -> tuple[str, ...]:
    resolved_metadata = metadata or load_application_metadata()
    findings: list[str] = []
    tables = _sorted_tables(resolved_metadata)
    if not tables:
        return ("No SQLAlchemy tables were registered on Base.metadata.",)

    observed_table_names = {table.name for table in tables}
    missing_tables = sorted(required_tables - observed_table_names)
    if missing_tables:
        findings.append(f"Missing required SQLAlchemy tables: {', '.join(missing_tables)}.")

    for table in tables:
        if not SNAKE_CASE_PATTERN.match(table.name):
            findings.append(f"{table.name} is not snake_case.")
        primary_key_columns = [column.name for column in table.primary_key.columns]
        if not primary_key_columns:
            findings.append(f"{table.name} does not define a primary key.")
        for column in table.columns:
            if not SNAKE_CASE_PATTERN.match(column.name):
                findings.append(f"{table.name}.{column.name} is not snake_case.")
            if column.primary_key and column.nullable:
                findings.append(f"{table.name}.{column.name} is a nullable primary key column.")
            if column.foreign_keys and not (bool(column.index) or column.primary_key):
                findings.append(f"{table.name}.{column.name} has a foreign key but no index flag.")

    return tuple(findings)


def serialize_schema_contract(contract: dict[str, Any]) -> str:
    return json.dumps(contract, indent=2, sort_keys=True) + "\n"


def write_schema_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    metadata: MetaData | None = None,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        serialize_schema_contract(build_schema_contract(metadata)),
        encoding="utf-8",
    )


def check_schema_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    metadata: MetaData | None = None,
    required_tables: frozenset[str] = REQUIRED_TABLES,
) -> tuple[bool, str]:
    resolved_metadata = metadata or load_application_metadata()
    findings = validate_schema_metadata(resolved_metadata, required_tables)
    if findings:
        return False, "SQLAlchemy schema contract violations: " + "; ".join(findings)

    if not output_path.is_file():
        return False, f"SQLAlchemy schema contract does not exist: {output_path}"

    expected = serialize_schema_contract(build_schema_contract(resolved_metadata))
    actual = output_path.read_text(encoding="utf-8")
    if actual != expected:
        return False, f"SQLAlchemy schema contract is stale: {output_path}"

    table_count = build_schema_contract(resolved_metadata)["summary"]["table_count"]
    return True, f"SQLAlchemy schema contract is current for {table_count} tables: {output_path}"


def load_application_metadata() -> MetaData:
    importlib.import_module("forgeml.platform.database.models")
    return Base.metadata


def _table_contract(table: Table) -> dict[str, Any]:
    return {
        "name": table.name,
        "columns": [_column_contract(column) for column in table.columns],
        "primary_key": [column.name for column in table.primary_key.columns],
        "foreign_keys": sorted(
            {
                f"{foreign_key.parent.name}->{foreign_key.column.table.name}.{foreign_key.column.name}"
                for column in table.columns
                for foreign_key in column.foreign_keys
            }
        ),
        "indexes": [
            {
                "name": index.name or "",
                "columns": [column.name for column in index.columns],
                "unique": bool(index.unique),
            }
            for index in sorted(
                table.indexes,
                key=lambda item: (item.name or "", tuple(column.name for column in item.columns)),
            )
        ],
        "unique_constraints": [
            {
                "name": constraint.name or "",
                "columns": [column.name for column in constraint.columns],
            }
            for constraint in sorted(
                (
                    constraint
                    for constraint in table.constraints
                    if isinstance(constraint, UniqueConstraint)
                ),
                key=lambda item: (
                    item.name or "",
                    tuple(column.name for column in item.columns),
                ),
            )
        ],
    }


def _column_contract(column: Any) -> dict[str, Any]:
    return {
        "name": column.name,
        "type": _column_type(column),
        "nullable": bool(column.nullable),
        "primary_key": bool(column.primary_key),
        "index": bool(column.index),
        "unique": bool(column.unique),
        "has_python_default": column.default is not None,
        "has_server_default": column.server_default is not None,
        "foreign_keys": sorted(
            f"{foreign_key.column.table.name}.{foreign_key.column.name}"
            for foreign_key in column.foreign_keys
        ),
    }


def _column_type(column: Any) -> str:
    return column.type.compile(dialect=POSTGRES_DIALECT)


def _sorted_tables(metadata: MetaData) -> list[Table]:
    return sorted(metadata.tables.values(), key=lambda table: table.name)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify ForgeML SQLAlchemy metadata schema contract."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the checked-in SQLAlchemy schema contract.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate the checked-in SQLAlchemy schema contract.",
    )
    args = parser.parse_args(argv)

    if args.write:
        write_schema_contract(args.output)
        print(f"Wrote SQLAlchemy schema contract: {args.output}")
        return 0

    passed, detail = check_schema_contract(args.output)
    print(("PASS " if passed else "FAIL ") + detail)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
