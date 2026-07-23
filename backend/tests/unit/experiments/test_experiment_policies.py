import pytest

from forgeml.modules.experiments.domain.policies import (
    build_experiment_slug,
    validate_model_type,
    validate_tracking_payload,
)
from forgeml.platform.domain.errors import DomainValidationError


def test_build_experiment_slug_normalizes_names() -> None:
    assert build_experiment_slug(" Fraud Risk XGBoost / Baseline ") == "fraud-risk-xgboost-baseline"


def test_validate_model_type_supports_initial_platform_models() -> None:
    validate_model_type("pytorch")
    validate_model_type("xgboost")
    validate_model_type("lightgbm")
    validate_model_type("semantic-search")


def test_validate_tracking_payload_rejects_non_finite_metrics() -> None:
    with pytest.raises(DomainValidationError):
        validate_tracking_payload({}, {"auc": float("nan")})
