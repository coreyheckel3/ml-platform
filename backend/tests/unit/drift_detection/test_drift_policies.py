import pytest

from forgeml.modules.drift_detection.domain.policies import (
    build_drift_profile_slug,
    validate_baseline_profile,
    validate_drift_threshold,
)
from forgeml.platform.domain.errors import DomainValidationError


def test_drift_policies_validate_numeric_and_categorical_baselines() -> None:
    baseline = {
        "amount": {"type": "numeric", "mean": 100.0, "std": 25.0, "threshold": 0.2},
        "merchant_category": {
            "type": "categorical",
            "distribution": {"travel": 0.4, "grocery": 0.6},
            "threshold": 0.3,
        },
    }

    validate_baseline_profile(baseline)

    assert build_drift_profile_slug("Fraud Risk Baseline") == "fraud-risk-baseline"


def test_drift_policies_reject_invalid_baseline_feature_type() -> None:
    with pytest.raises(DomainValidationError):
        validate_baseline_profile({"amount": {"type": "vector", "mean": 10, "std": 1}})


def test_drift_policies_reject_invalid_threshold() -> None:
    with pytest.raises(DomainValidationError):
        validate_drift_threshold(1.5)
