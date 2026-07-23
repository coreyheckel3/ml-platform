from dataclasses import dataclass
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from forgeml.main import create_app
from forgeml.modules.experiments.api.routes import get_experiment_service
from forgeml.modules.experiments.domain.entities import (
    Experiment,
    ExperimentArtifact,
    ExperimentRun,
    ExperimentRunStatus,
    ExperimentStatus,
)
from forgeml.platform.api.dependencies import get_current_principal
from forgeml.platform.security.rbac import Principal


@dataclass
class FakeExperimentService:
    organization_id: UUID
    project_id: UUID
    user_id: UUID
    experiment_id: UUID
    run_id: UUID
    artifact_id: UUID
    dataset_version_id: UUID
    feature_set_id: UUID

    def create_experiment(self, command, principal):
        assert command.name == "Fraud Risk Baseline"
        return self._experiment()

    def list_experiments(self, project_id, principal):
        assert project_id == self.project_id
        return [self._experiment()]

    def get_experiment(self, experiment_id, principal):
        assert experiment_id == self.experiment_id
        return self._experiment()

    def start_run(self, command, principal):
        assert command.run_name == "xgb-depth-6"
        return self._run(ExperimentRunStatus.RUNNING)

    def list_runs(self, experiment_id, principal):
        assert experiment_id == self.experiment_id
        return [self._run(ExperimentRunStatus.RUNNING)]

    def get_run(self, run_id, principal):
        assert run_id == self.run_id
        return self._run(ExperimentRunStatus.RUNNING)

    def log_metrics(self, command, principal):
        assert command.metrics["auc"] == 0.94
        return self._run(ExperimentRunStatus.RUNNING, metrics={"auc": 0.94})

    def log_artifact(self, command, principal):
        assert command.name == "model"
        return self._artifact()

    def list_artifacts(self, experiment_run_id, principal):
        assert experiment_run_id == self.run_id
        return [self._artifact()]

    def complete_run(self, command, principal):
        assert command.status == ExperimentRunStatus.SUCCEEDED
        return self._run(ExperimentRunStatus.SUCCEEDED, metrics={"auc": 0.94})

    def _experiment(self) -> Experiment:
        return Experiment(
            id=self.experiment_id,
            organization_id=self.organization_id,
            project_id=self.project_id,
            name="Fraud Risk Baseline",
            slug="fraud-risk-baseline",
            description="Baseline fraud models.",
            owner_user_id=self.user_id,
            status=ExperimentStatus.ACTIVE,
        )

    def _run(
        self,
        status: ExperimentRunStatus,
        metrics: dict[str, float] | None = None,
    ) -> ExperimentRun:
        return ExperimentRun(
            id=self.run_id,
            experiment_id=self.experiment_id,
            project_id=self.project_id,
            run_name="xgb-depth-6",
            status=status,
            model_type="xgboost",
            started_by=self.user_id,
            dataset_version_id=self.dataset_version_id,
            feature_set_id=self.feature_set_id,
            parameters={"max_depth": 6},
            metrics=metrics or {},
            artifact_uri="s3://forgeml/experiments/run-1",
            evaluation_report={"threshold": 0.71} if metrics else {},
            error_message=None,
        )

    def _artifact(self) -> ExperimentArtifact:
        return ExperimentArtifact(
            id=self.artifact_id,
            experiment_run_id=self.run_id,
            name="model",
            artifact_type="pickle",
            uri="s3://forgeml/experiments/run-1/model.pkl",
            metadata={"sha256": "abc"},
        )


def test_experiment_routes_expose_tracking_lifecycle() -> None:
    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    service = FakeExperimentService(
        organization_id=organization_id,
        project_id=project_id,
        user_id=user_id,
        experiment_id=uuid4(),
        run_id=uuid4(),
        artifact_id=uuid4(),
        dataset_version_id=uuid4(),
        feature_set_id=uuid4(),
    )
    app = create_app()
    app.dependency_overrides[get_experiment_service] = lambda: service
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        user_id=str(user_id),
        email="owner@example.com",
        organization_id=str(organization_id),
        permissions=frozenset({"*"}),
    )
    client = TestClient(app)

    created = client.post(
        f"/api/v1/projects/{project_id}/experiments",
        json={"name": "Fraud Risk Baseline", "description": "Baseline fraud models."},
    )
    listed = client.get(f"/api/v1/projects/{project_id}/experiments")
    started = client.post(
        f"/api/v1/experiments/{service.experiment_id}/runs",
        json={
            "run_name": "xgb-depth-6",
            "model_type": "xgboost",
            "artifact_uri": "s3://forgeml/experiments/run-1",
            "dataset_version_id": str(service.dataset_version_id),
            "feature_set_id": str(service.feature_set_id),
            "parameters": {"max_depth": 6},
        },
    )
    metrics = client.post(
        f"/api/v1/experiment-runs/{service.run_id}/metrics",
        json={"metrics": {"auc": 0.94}, "evaluation_report": {"threshold": 0.71}},
    )
    artifact = client.post(
        f"/api/v1/experiment-runs/{service.run_id}/artifacts",
        json={
            "name": "model",
            "artifact_type": "pickle",
            "uri": "s3://forgeml/experiments/run-1/model.pkl",
            "metadata": {"sha256": "abc"},
        },
    )
    completed = client.post(
        f"/api/v1/experiment-runs/{service.run_id}/complete",
        json={"status": "succeeded", "metrics": {"auc": 0.94}},
    )

    assert created.status_code == 201
    assert created.json()["slug"] == "fraud-risk-baseline"
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == str(service.experiment_id)
    assert started.status_code == 201
    assert started.json()["parameters"]["max_depth"] == 6
    assert metrics.status_code == 200
    assert metrics.json()["metrics"]["auc"] == 0.94
    assert artifact.status_code == 201
    assert artifact.json()["artifact_type"] == "pickle"
    assert completed.status_code == 200
    assert completed.json()["status"] == "succeeded"
