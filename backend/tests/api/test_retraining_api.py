from dataclasses import dataclass
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from forgeml.main import create_app
from forgeml.modules.retraining.api.routes import get_retraining_service
from forgeml.modules.retraining.domain.entities import (
    RetrainingDecision,
    RetrainingEvaluation,
    RetrainingPolicy,
    RetrainingPolicyStatus,
    RetrainingRun,
    RetrainingRunStatus,
    RetrainingTriggerType,
)
from forgeml.platform.api.dependencies import get_current_principal
from forgeml.platform.security.rbac import Principal

_UNSET = object()


@dataclass
class FakeRetrainingService:
    organization_id: UUID
    project_id: UUID
    deployment_id: UUID
    policy_id: UUID
    run_id: UUID
    training_run_id: UUID
    drift_report_id: UUID
    user_id: UUID

    def create_policy(self, command, principal):
        assert command.name == "Fraud Drift Retraining"
        return self._policy()

    def list_policies(self, project_id, principal):
        assert project_id == self.project_id
        return [self._policy()]

    def evaluate_policy(self, command, principal):
        assert command.drift_report_id == self.drift_report_id
        return RetrainingEvaluation(
            policy_id=self.policy_id,
            decision=RetrainingDecision.TRIGGERED,
            triggered=True,
            reason="Retraining run was queued.",
            run=self._run(RetrainingRunStatus.QUEUED),
        )

    def trigger_run(self, command, principal):
        assert command.policy_id == self.policy_id
        return RetrainingEvaluation(
            policy_id=self.policy_id,
            decision=RetrainingDecision.PENDING_APPROVAL,
            triggered=True,
            reason="Retraining run is waiting for approval.",
            run=self._run(RetrainingRunStatus.PENDING_APPROVAL, training_run_id=None),
        )

    def list_runs(self, project_id, principal):
        assert project_id == self.project_id
        return [self._run(RetrainingRunStatus.QUEUED)]

    def get_run(self, run_id, principal):
        assert run_id == self.run_id
        return self._run(RetrainingRunStatus.QUEUED)

    def approve_run(self, run_id, principal):
        assert run_id == self.run_id
        return self._run(RetrainingRunStatus.QUEUED, approved_by=self.user_id)

    def reject_run(self, run_id, principal):
        assert run_id == self.run_id
        return self._run(
            RetrainingRunStatus.REJECTED,
            training_run_id=None,
            rejected_by=self.user_id,
        )

    def _policy(self) -> RetrainingPolicy:
        return RetrainingPolicy(
            id=self.policy_id,
            organization_id=self.organization_id,
            project_id=self.project_id,
            deployment_id=self.deployment_id,
            name="Fraud Drift Retraining",
            slug="fraud-drift-retraining",
            description="Retrain fraud model when drift breaches thresholds.",
            trigger_type=RetrainingTriggerType.DRIFT,
            trigger_config={"min_drift_score": 0.2, "min_drifted_features": 1},
            training_template={
                "experiment_id": str(uuid4()),
                "dataset_version_id": str(uuid4()),
                "feature_set_id": None,
                "run_name_prefix": "fraud-retrain",
                "algorithm": "xgboost",
                "model_type": "xgboost",
                "objective_metric_name": "auc",
                "hyperparameters": {"max_depth": 6},
            },
            cooldown_seconds=3600,
            max_runs_per_day=3,
            approval_required=False,
            enabled=True,
            status=RetrainingPolicyStatus.ACTIVE,
            created_by=self.user_id,
        )

    def _run(
        self,
        status: RetrainingRunStatus,
        *,
        training_run_id: UUID | None | object = _UNSET,
        approved_by: UUID | None = None,
        rejected_by: UUID | None = None,
    ) -> RetrainingRun:
        resolved_training_run_id = (
            self.training_run_id if training_run_id is _UNSET else training_run_id
        )
        return RetrainingRun(
            id=self.run_id,
            organization_id=self.organization_id,
            project_id=self.project_id,
            policy_id=self.policy_id,
            deployment_id=self.deployment_id,
            trigger_type=RetrainingTriggerType.DRIFT,
            drift_report_id=self.drift_report_id,
            alert_event_id=None,
            training_run_id=resolved_training_run_id,
            status=status,
            reason="Nightly drift evaluation.",
            training_config={
                "run_name": "fraud-retrain-drift-abcdef12",
                "algorithm": "xgboost",
            },
            decision_metadata={"drift_score": 0.42},
            requested_by=self.user_id,
            approved_by=approved_by,
            rejected_by=rejected_by,
        )


def test_retraining_routes_expose_policy_and_run_lifecycle() -> None:
    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    service = FakeRetrainingService(
        organization_id=organization_id,
        project_id=project_id,
        deployment_id=uuid4(),
        policy_id=uuid4(),
        run_id=uuid4(),
        training_run_id=uuid4(),
        drift_report_id=uuid4(),
        user_id=user_id,
    )
    app = create_app()
    app.dependency_overrides[get_retraining_service] = lambda: service
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        user_id=str(user_id),
        email="owner@example.com",
        organization_id=str(organization_id),
        permissions=frozenset({"*"}),
    )
    client = TestClient(app)

    created = client.post(
        f"/api/v1/projects/{project_id}/retraining-policies",
        json={
            "deployment_id": str(service.deployment_id),
            "name": "Fraud Drift Retraining",
            "description": "Retrain fraud model when drift breaches thresholds.",
            "trigger_type": "drift",
            "trigger_config": {"min_drift_score": 0.2, "min_drifted_features": 1},
            "training_template": {
                "experiment_id": str(uuid4()),
                "dataset_version_id": str(uuid4()),
                "run_name_prefix": "fraud-retrain",
                "algorithm": "xgboost",
                "model_type": "xgboost",
                "objective_metric_name": "auc",
                "hyperparameters": {"max_depth": 6},
            },
        },
    )
    policies = client.get(f"/api/v1/projects/{project_id}/retraining-policies")
    evaluated = client.post(
        f"/api/v1/retraining-policies/{service.policy_id}/evaluate",
        json={"drift_report_id": str(service.drift_report_id)},
    )
    triggered = client.post(
        f"/api/v1/retraining-policies/{service.policy_id}/trigger",
        json={"reason": "Operator requested retraining."},
    )
    runs = client.get(f"/api/v1/projects/{project_id}/retraining-runs")
    run = client.get(f"/api/v1/retraining-runs/{service.run_id}")
    approved = client.post(f"/api/v1/retraining-runs/{service.run_id}/approve")
    rejected = client.post(f"/api/v1/retraining-runs/{service.run_id}/reject")

    assert created.status_code == 201
    assert created.json()["slug"] == "fraud-drift-retraining"
    assert policies.status_code == 200
    assert policies.json()["items"][0]["name"] == "Fraud Drift Retraining"
    assert evaluated.status_code == 202
    assert evaluated.json()["decision"] == "triggered"
    assert triggered.status_code == 202
    assert triggered.json()["decision"] == "pending_approval"
    assert runs.status_code == 200
    assert runs.json()["items"][0]["training_run_id"] == str(service.training_run_id)
    assert run.status_code == 200
    assert approved.status_code == 200
    assert approved.json()["approved_by"] == str(user_id)
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
