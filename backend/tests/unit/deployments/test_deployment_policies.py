import pytest

from forgeml.modules.deployments.domain.entities import (
    DeploymentHealthStatus,
    DeploymentRevisionStatus,
    ModelVersionDeploymentReference,
)
from forgeml.modules.deployments.domain.policies import (
    build_deployment_slug,
    parse_deployment_environment,
    validate_deployable_model_version,
    validate_health_check,
    validate_rollback_target,
    validate_traffic_percentage,
)
from forgeml.platform.domain.errors import DomainValidationError


def test_build_deployment_slug_normalizes_names() -> None:
    assert build_deployment_slug(" Fraud Risk Production ") == "fraud-risk-production"


def test_parse_deployment_environment_accepts_supported_values() -> None:
    assert parse_deployment_environment("production").value == "production"
    assert parse_deployment_environment("staging").value == "staging"


def test_deployable_model_version_requires_approved_status(model_version_reference) -> None:
    rejected = ModelVersionDeploymentReference(
        id=model_version_reference.id,
        registered_model_id=model_version_reference.registered_model_id,
        organization_id=model_version_reference.organization_id,
        project_id=model_version_reference.project_id,
        version=model_version_reference.version,
        status="candidate",
        artifact_uri=model_version_reference.artifact_uri,
        model_format=model_version_reference.model_format,
    )

    with pytest.raises(DomainValidationError):
        validate_deployable_model_version(rejected)


def test_validate_traffic_percentage_rejects_invalid_values() -> None:
    with pytest.raises(DomainValidationError):
        validate_traffic_percentage(101)


def test_validate_health_check_rejects_invalid_error_rate() -> None:
    with pytest.raises(DomainValidationError):
        validate_health_check(
            status=DeploymentHealthStatus.HEALTHY,
            latency_ms=12.0,
            error_rate=1.5,
        )


def test_validate_rollback_target_requires_healthy_revision() -> None:
    with pytest.raises(DomainValidationError):
        validate_rollback_target(DeploymentRevisionStatus.DEGRADED)


@pytest.fixture
def model_version_reference():
    from uuid import uuid4

    return ModelVersionDeploymentReference(
        id=uuid4(),
        registered_model_id=uuid4(),
        organization_id=uuid4(),
        project_id=uuid4(),
        version=1,
        status="approved",
        artifact_uri="s3://forgeml/models/model-v1",
        model_format="xgboost-booster",
    )
