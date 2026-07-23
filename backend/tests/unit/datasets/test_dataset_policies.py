import pytest

from forgeml.modules.datasets.domain.policies import (
    build_dataset_slug,
    infer_schema_from_csv,
    schema_hash,
)
from forgeml.platform.domain.errors import DomainValidationError


def test_build_dataset_slug_normalizes_names() -> None:
    assert build_dataset_slug("  Fraud Transactions 2026/07 ") == "fraud-transactions-2026-07"


def test_infer_schema_from_csv_detects_types_and_nullability() -> None:
    fields, row_count = infer_schema_from_csv(
        "transaction_id,amount,is_fraud,event_time,merchant\n"
        "1,12.50,false,2026-07-18T12:00:00Z,coffee\n"
        "2,,true,2026-07-18T12:03:00Z,\n"
    )

    assert row_count == 2
    assert [(field.name, field.dtype, field.nullable) for field in fields] == [
        ("transaction_id", "integer", False),
        ("amount", "float", True),
        ("is_fraud", "boolean", False),
        ("event_time", "datetime", False),
        ("merchant", "string", True),
    ]
    assert len(schema_hash(fields)) == 64


def test_infer_schema_rejects_duplicate_headers() -> None:
    with pytest.raises(DomainValidationError):
        infer_schema_from_csv("id,id\n1,2\n")

