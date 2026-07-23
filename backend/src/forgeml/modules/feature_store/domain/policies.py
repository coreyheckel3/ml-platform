import re

from forgeml.modules.feature_store.domain.entities import FeatureDefinition
from forgeml.platform.domain.errors import DomainValidationError

_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")
_FEATURE_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_ALLOWED_DTYPES = {
    "string",
    "integer",
    "float",
    "boolean",
    "datetime",
    "categorical",
    "vector",
    "json",
}


def build_feature_set_slug(name: str) -> str:
    normalized = _SLUG_PATTERN.sub("-", name.strip().lower()).strip("-")
    if not normalized:
        raise DomainValidationError("Feature set name must contain at least one letter or number.")
    return normalized[:80]


def validate_feature_set_name(name: str) -> None:
    stripped = name.strip()
    if len(stripped) < 3:
        raise DomainValidationError("Feature set name must be at least 3 characters.")
    if len(stripped) > 120:
        raise DomainValidationError("Feature set name must be at most 120 characters.")


def validate_entity_key(entity_key: str) -> None:
    if not _FEATURE_NAME_PATTERN.match(entity_key):
        raise DomainValidationError("Entity key must be a valid feature identifier.")


def validate_feature_name(name: str) -> None:
    if not _FEATURE_NAME_PATTERN.match(name):
        raise DomainValidationError("Feature names must be valid Python-style identifiers.")


def validate_feature_dtype(dtype: str) -> None:
    if dtype not in _ALLOWED_DTYPES:
        allowed = ", ".join(sorted(_ALLOWED_DTYPES))
        raise DomainValidationError(f"Feature dtype must be one of: {allowed}.")


def validate_feature_definitions(definitions: tuple[FeatureDefinition, ...]) -> None:
    if not definitions:
        raise DomainValidationError("At least one feature definition is required.")
    seen: set[str] = set()
    for definition in definitions:
        validate_feature_name(definition.name)
        validate_feature_dtype(definition.dtype)
        normalized = definition.name.lower()
        if normalized in seen:
            raise DomainValidationError("Feature names must be unique within a feature set.")
        seen.add(normalized)


def validate_pipeline_name(name: str) -> None:
    stripped = name.strip()
    if len(stripped) < 3:
        raise DomainValidationError("Feature pipeline name must be at least 3 characters.")
    if len(stripped) > 120:
        raise DomainValidationError("Feature pipeline name must be at most 120 characters.")


def validate_code_ref(code_ref: str) -> None:
    stripped = code_ref.strip()
    if len(stripped) < 3:
        raise DomainValidationError("Feature pipeline code reference is required.")
    if len(stripped) > 512:
        raise DomainValidationError("Feature pipeline code reference is too long.")

