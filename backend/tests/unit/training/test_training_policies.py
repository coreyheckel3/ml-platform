import pytest

from forgeml.modules.training.domain.entities import TrainingRunStatus
from forgeml.modules.training.domain.policies import (
    validate_metrics,
    validate_terminal_status,
    validate_training_run_request,
)
from forgeml.platform.domain.errors import DomainValidationError


def test_validate_training_request_requires_data_input() -> None:
    with pytest.raises(DomainValidationError):
        validate_training_run_request(
            algorithm="xgboost",
            model_type="xgboost",
            objective_metric_name="auc",
            hyperparameters={},
            dataset_version_id=None,
            feature_set_id=None,
        )


def test_validate_metrics_rejects_non_numeric_values() -> None:
    with pytest.raises(DomainValidationError):
        validate_metrics({"auc": "high"})  # type: ignore[dict-item]


def test_validate_terminal_status_rejects_non_terminal_state() -> None:
    with pytest.raises(DomainValidationError):
        validate_terminal_status(TrainingRunStatus.RUNNING)
