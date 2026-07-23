import re

from forgeml.modules.deployments.domain.entities import (
    DeploymentEnvironment,
    DeploymentHealthStatus,
    DeploymentRevisionStatus,
    ModelVersionDeploymentReference,
)
from forgeml.platform.domain.errors import DomainValidationError

_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")
_SERVING_IMAGE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@-]*$")


def build_deployment_slug(name: str) -> str:
    normalized = _SLUG_PATTERN.sub("-", name.strip().lower()).strip("-")
    if not normalized:
        raise DomainValidationError("Deployment name must contain at least one letter or number.")
    return normalized[:80]


def validate_deployment_name(name: str) -> None:
    stripped = name.strip()
    if len(stripped) < 3:
        raise DomainValidationError("Deployment name must be at least 3 characters.")
    if len(stripped) > 120:
        raise DomainValidationError("Deployment name must be at most 120 characters.")


def parse_deployment_environment(environment: str) -> DeploymentEnvironment:
    try:
        return DeploymentEnvironment(environment.strip().lower())
    except ValueError as exc:
        allowed = ", ".join(environment.value for environment in DeploymentEnvironment)
        raise DomainValidationError(f"Deployment environment must be one of: {allowed}.") from exc


def validate_deployable_model_version(reference: ModelVersionDeploymentReference) -> None:
    if reference.status != "approved":
        raise DomainValidationError("Only approved model versions can be deployed.")
    if len(reference.artifact_uri.strip()) < 3:
        raise DomainValidationError("Model version must expose an artifact URI.")


def validate_serving_image(serving_image: str) -> None:
    stripped = serving_image.strip()
    if len(stripped) < 3 or len(stripped) > 512:
        raise DomainValidationError("Serving image must be between 3 and 512 characters.")
    if not _SERVING_IMAGE_PATTERN.match(stripped):
        raise DomainValidationError("Serving image contains unsupported characters.")


def validate_runtime_config(runtime_config: dict[str, object]) -> None:
    if len(runtime_config) > 100:
        raise DomainValidationError("Deployment runtime config cannot exceed 100 keys.")


def validate_traffic_percentage(traffic_percentage: int) -> None:
    if traffic_percentage < 0 or traffic_percentage > 100:
        raise DomainValidationError("Traffic percentage must be between 0 and 100.")


def validate_health_check(
    *,
    status: DeploymentHealthStatus,
    latency_ms: float,
    error_rate: float,
) -> None:
    if status == DeploymentHealthStatus.UNKNOWN:
        raise DomainValidationError("Health check status cannot be unknown.")
    if latency_ms < 0:
        raise DomainValidationError("Health check latency cannot be negative.")
    if error_rate < 0 or error_rate > 1:
        raise DomainValidationError("Health check error rate must be between 0 and 1.")


def validate_rollback_target(status: DeploymentRevisionStatus) -> None:
    if status != DeploymentRevisionStatus.HEALTHY:
        raise DomainValidationError("Rollback target must be a healthy deployment revision.")
