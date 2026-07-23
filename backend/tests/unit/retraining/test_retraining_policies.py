from uuid import uuid4

import pytest

from forgeml.modules.retraining.domain.entities import (
    AlertRetrainingSignal,
    DriftRetrainingSignal,
    RetrainingPolicy,
    RetrainingPolicyStatus,
    RetrainingTriggerType,
)
from forgeml.modules.retraining.domain.policies import (
    normalize_training_template,
    normalize_trigger_config,
    retraining_policy_accepts_alert,
    retraining_policy_accepts_drift,
)
from forgeml.platform.domain.errors import DomainValidationError


def test_retraining_policy_normalizes_drift_trigger_and_training_template() -> None:
    experiment_id = uuid4()
    dataset_version_id = uuid4()

    trigger_config = normalize_trigger_config(
        RetrainingTriggerType.DRIFT,
        {"min_drift_score": 0.25, "min_drifted_features": 2},
    )
    template = normalize_training_template(
        {
            "experiment_id": str(experiment_id),
            "dataset_version_id": str(dataset_version_id),
            "run_name_prefix": "fraud-retrain",
            "algorithm": "xgboost",
            "model_type": "xgboost",
            "objective_metric_name": "auc",
            "hyperparameters": {"max_depth": 6},
        }
    )

    assert trigger_config["min_drift_score"] == 0.25
    assert trigger_config["min_drifted_features"] == 2
    assert template["experiment_id"] == str(experiment_id)
    assert template["feature_set_id"] is None


def test_retraining_policy_rejects_invalid_manual_trigger_config() -> None:
    with pytest.raises(DomainValidationError):
        normalize_trigger_config(RetrainingTriggerType.MANUAL, {"min_drift_score": 0.1})


def test_retraining_policy_matches_drift_and_alert_signals() -> None:
    organization_id = uuid4()
    project_id = uuid4()
    deployment_id = uuid4()
    policy = RetrainingPolicy(
        id=uuid4(),
        organization_id=organization_id,
        project_id=project_id,
        deployment_id=deployment_id,
        name="Fraud Drift Retraining",
        slug="fraud-drift-retraining",
        description="",
        trigger_type=RetrainingTriggerType.DRIFT,
        trigger_config={"min_drift_score": 0.2, "min_drifted_features": 1},
        training_template={},
        cooldown_seconds=3600,
        max_runs_per_day=3,
        approval_required=True,
        enabled=True,
        status=RetrainingPolicyStatus.ACTIVE,
        created_by=uuid4(),
    )
    drift_signal = DriftRetrainingSignal(
        drift_report_id=uuid4(),
        organization_id=organization_id,
        project_id=project_id,
        deployment_id=deployment_id,
        endpoint_id=uuid4(),
        drift_score=0.42,
        drifted_feature_count=2,
        evaluated_feature_count=4,
        status="completed",
    )
    alert_policy = RetrainingPolicy(
        **{
            **policy.__dict__,
            "id": uuid4(),
            "trigger_type": RetrainingTriggerType.ALERT,
            "trigger_config": {"severities": ["critical"]},
        }
    )
    alert_signal = AlertRetrainingSignal(
        alert_event_id=uuid4(),
        organization_id=organization_id,
        project_id=project_id,
        endpoint_id=uuid4(),
        deployment_id=deployment_id,
        severity="critical",
        status="open",
        observed_value=0.31,
        threshold=0.1,
        metadata={},
    )

    drift_matches, _ = retraining_policy_accepts_drift(policy, drift_signal)
    alert_matches, _ = retraining_policy_accepts_alert(alert_policy, alert_signal)

    assert drift_matches
    assert alert_matches
