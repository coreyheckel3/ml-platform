from dataclasses import dataclass
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from forgeml.main import create_app
from forgeml.modules.training.api.routes import get_training_run_service
from forgeml.modules.training.domain.entities import (
    TrainingRun,
    TrainingRunEvent,
    TrainingRunStatus,
)
from forgeml.platform.api.dependencies import get_current_principal
from forgeml.platform.security.rbac import Principal


@dataclass
class FakeTrainingRunService:
    organization_id: UUID
    project_id: UUID
    user_id: UUID
    experiment_id: UUID
    experiment_run_id: UUID
    dataset_version_id: UUID
    training_run_id: UUID
    event_id: UUID

    def start_training_run(self, command, principal):
        assert command.algorithm == "xgboost"
        return self._training_run(TrainingRunStatus.QUEUED)

    def list_training_runs(self, project_id, principal):
        assert project_id == self.project_id
        return [self._training_run(TrainingRunStatus.QUEUED)]

    def get_training_run(self, training_run_id, principal):
        assert training_run_id == self.training_run_id
        return self._training_run(TrainingRunStatus.QUEUED)

    def record_result(self, command, principal):
        assert command.metrics["auc"] == 0.94
        return self._training_run(TrainingRunStatus.SUCCEEDED, metrics={"auc": 0.94})

    def cancel_training_run(self, training_run_id, principal):
        assert training_run_id == self.training_run_id
        return self._training_run(TrainingRunStatus.CANCELED)

    def list_events(self, training_run_id, principal):
        assert training_run_id == self.training_run_id
        return [
            TrainingRunEvent(
                id=self.event_id,
                training_run_id=self.training_run_id,
                event_type="queued",
                message="Training run was queued.",
                metadata={"orchestrator_run_id": "workflow-1"},
            )
        ]

    def _training_run(
        self,
        status: TrainingRunStatus,
        metrics: dict[str, float] | None = None,
    ) -> TrainingRun:
        return TrainingRun(
            id=self.training_run_id,
            organization_id=self.organization_id,
            project_id=self.project_id,
            experiment_id=self.experiment_id,
            experiment_run_id=self.experiment_run_id,
            dataset_version_id=self.dataset_version_id,
            feature_set_id=None,
            algorithm="xgboost",
            model_type="xgboost",
            objective_metric_name="auc",
            hyperparameters={"max_depth": 6},
            status=status,
            requested_by=self.user_id,
            artifact_uri="s3://forgeml/training-runs/run-1",
            orchestrator_run_id="workflow-1",
            metrics=metrics or {},
            error_message=None,
        )


def test_training_routes_expose_training_lifecycle() -> None:
    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    service = FakeTrainingRunService(
        organization_id=organization_id,
        project_id=project_id,
        user_id=user_id,
        experiment_id=uuid4(),
        experiment_run_id=uuid4(),
        dataset_version_id=uuid4(),
        training_run_id=uuid4(),
        event_id=uuid4(),
    )
    app = create_app()
    app.dependency_overrides[get_training_run_service] = lambda: service
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        user_id=str(user_id),
        email="owner@example.com",
        organization_id=str(organization_id),
        permissions=frozenset({"*"}),
    )
    client = TestClient(app)

    started = client.post(
        f"/api/v1/projects/{project_id}/training-runs",
        json={
            "experiment_id": str(service.experiment_id),
            "run_name": "fraud-xgb-depth-6",
            "dataset_version_id": str(service.dataset_version_id),
            "algorithm": "xgboost",
            "model_type": "xgboost",
            "objective_metric_name": "auc",
            "hyperparameters": {"max_depth": 6},
        },
    )
    listed = client.get(f"/api/v1/projects/{project_id}/training-runs")
    result = client.post(
        f"/api/v1/training-runs/{service.training_run_id}/result",
        json={
            "status": "succeeded",
            "metrics": {"auc": 0.94},
            "evaluation_report": {"threshold": 0.71},
        },
    )
    events = client.get(f"/api/v1/training-runs/{service.training_run_id}/events")
    canceled = client.post(f"/api/v1/training-runs/{service.training_run_id}/cancel")

    assert started.status_code == 202
    assert started.json()["status"] == "queued"
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == str(service.training_run_id)
    assert result.status_code == 200
    assert result.json()["metrics"]["auc"] == 0.94
    assert events.status_code == 200
    assert events.json()["items"][0]["event_type"] == "queued"
    assert canceled.status_code == 200
    assert canceled.json()["status"] == "canceled"
