import re

from forgeml.platform.domain.errors import DomainValidationError

_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


def build_project_slug(name: str) -> str:
    normalized = _SLUG_PATTERN.sub("-", name.strip().lower()).strip("-")
    if not normalized:
        raise DomainValidationError("Project name must contain at least one letter or number.")
    return normalized[:80]


def validate_project_name(name: str) -> None:
    stripped = name.strip()
    if len(stripped) < 3:
        raise DomainValidationError("Project name must be at least 3 characters.")
    if len(stripped) > 120:
        raise DomainValidationError("Project name must be at most 120 characters.")
