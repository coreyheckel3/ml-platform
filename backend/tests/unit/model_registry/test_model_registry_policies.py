import pytest

from forgeml.modules.model_registry.domain.entities import (
    ModelApprovalStatus,
    TrainingRunReference,
)
from forgeml.modules.model_registry.domain.policies import (
    build_registered_model_slug,
    normalize_model_format,
    normalize_task_type,
    validate_approval_decision,
    validate_model_signature,
    validate_training_run_reference,
)
from forgeml.platform.domain.errors import DomainValidationError


def test_build_registered_model_slug_normalizes_names() -> None:
    assert build_registered_model_slug(" Fraud Risk XGB / Champion ") == "fraud-risk-xgb-champion"


def test_registry_policy_accepts_supported_tasks_and_formats() -> None:
    assert normalize_task_type("classification") == "classification"
    assert normalize_task_type("recommendation") == "recommendation"
    assert normalize_model_format("xgboost-booster") == "xgboost-booster"
    assert normalize_model_format("torchscript") == "torchscript"


def test_model_signature_requires_inputs_and_outputs() -> None:
    with pytest.raises(DomainValidationError):
        validate_model_signature({"inputs": [{"name": "amount"}]})


def test_training_reference_requires_succeeded_run(training_reference) -> None:
    failed = TrainingRunReference(
        id=training_reference.id,
        organization_id=training_reference.organization_id,
        project_id=training_reference.project_id,
        experiment_id=training_reference.experiment_id,
        experiment_run_id=training_reference.experiment_run_id,
        dataset_version_id=training_reference.dataset_version_id,
        feature_set_id=training_reference.feature_set_id,
        status="failed",
        artifact_uri=training_reference.artifact_uri,
        model_type=training_reference.model_type,
        metrics=training_reference.metrics,
    )

    with pytest.raises(DomainValidationError):
        validate_training_run_reference(failed)


def test_approval_decision_rejects_request_state() -> None:
    with pytest.raises(DomainValidationError):
        validate_approval_decision(ModelApprovalStatus.REQUESTED)


@pytest.fixture
def training_reference():
    from uuid import uuid4

    return TrainingRunReference(
        id=uuid4(),
        organization_id=uuid4(),
        project_id=uuid4(),
        experiment_id=uuid4(),
        experiment_run_id=uuid4(),
        dataset_version_id=uuid4(),
        feature_set_id=uuid4(),
        status="succeeded",
        artifact_uri="s3://forgeml/training-runs/run-1",
        model_type="xgboost",
        metrics={"auc": 0.94},
    )
