import csv
import hashlib
import io
import json
from datetime import UTC, datetime

from forgeml.modules.datasets.domain.entities import SchemaField
from forgeml.platform.domain.errors import DomainValidationError


def build_dataset_slug(name: str) -> str:
    import re

    normalized = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    if not normalized:
        raise DomainValidationError("Dataset name must contain at least one letter or number.")
    return normalized[:80]


def validate_dataset_name(name: str) -> None:
    stripped = name.strip()
    if len(stripped) < 3:
        raise DomainValidationError("Dataset name must be at least 3 characters.")
    if len(stripped) > 120:
        raise DomainValidationError("Dataset name must be at most 120 characters.")


def validate_dataset_version_metadata(
    *,
    content_hash: str,
    size_bytes: int,
    row_count: int,
) -> None:
    if not content_hash.strip():
        raise DomainValidationError("Dataset version content hash is required.")
    if size_bytes <= 0:
        raise DomainValidationError("Dataset version size must be greater than zero.")
    if row_count < 0:
        raise DomainValidationError("Dataset version row count cannot be negative.")


def schema_hash(fields: tuple[SchemaField, ...]) -> str:
    payload = [
        {"name": field.name, "dtype": field.dtype, "nullable": field.nullable}
        for field in fields
    ]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def infer_schema_from_csv(sample_csv: str) -> tuple[tuple[SchemaField, ...], int]:
    reader = csv.DictReader(io.StringIO(sample_csv))
    if not reader.fieldnames:
        raise DomainValidationError("CSV sample must include a header row.")

    normalized_headers = [header.strip() for header in reader.fieldnames]
    if len(set(normalized_headers)) != len(normalized_headers):
        raise DomainValidationError("CSV sample contains duplicate column names.")
    if any(not header for header in normalized_headers):
        raise DomainValidationError("CSV sample contains an empty column name.")

    values_by_column: dict[str, list[str]] = {header: [] for header in normalized_headers}
    row_count = 0
    for row in reader:
        row_count += 1
        for header in normalized_headers:
            values_by_column[header].append((row.get(header) or "").strip())

    fields = tuple(
        SchemaField(
            name=header,
            dtype=_infer_dtype(values_by_column[header]),
            nullable=any(value == "" for value in values_by_column[header]),
        )
        for header in normalized_headers
    )
    return fields, row_count


def _infer_dtype(values: list[str]) -> str:
    non_empty = [value for value in values if value != ""]
    if not non_empty:
        return "string"
    if all(_is_bool(value) for value in non_empty):
        return "boolean"
    if all(_is_int(value) for value in non_empty):
        return "integer"
    if all(_is_float(value) for value in non_empty):
        return "float"
    if all(_is_datetime(value) for value in non_empty):
        return "datetime"
    return "string"


def _is_bool(value: str) -> bool:
    return value.lower() in {"true", "false", "0", "1"}


def _is_int(value: str) -> bool:
    try:
        int(value)
    except ValueError:
        return False
    return "." not in value


def _is_float(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True


def _is_datetime(value: str) -> bool:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return False
    return True

