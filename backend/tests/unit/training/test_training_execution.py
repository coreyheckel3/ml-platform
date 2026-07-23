from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from forgeml.modules.training.domain.entities import TrainingRun, TrainingRunStatus
from forgeml.modules.training.infrastructure.execution import (
    EXAMPLE_PROJECT_SLUG_PARAMETER,
    LocalExampleTrainingRunner,
)


def test_local_example_training_runner_executes_selected_example(tmp_path: Path) -> None:
    training_run = _training_run(
        algorithm="xgboost",
        objective_metric_name="auc",
        hyperparameters={EXAMPLE_PROJECT_SLUG_PARAMETER: "fraud-detection"},
    )
    runner = LocalExampleTrainingRunner(tmp_path)

    result = runner.run(training_run)

    assert runner.can_run(training_run)
    assert result.status == TrainingRunStatus.SUCCEEDED
    assert result.metrics["auc"] == 1.0
    assert result.evaluation_report["example_project_slug"] == "fraud-detection"
    assert result.runner_name == "local-example-training-runner"
    assert {artifact.name for artifact in result.artifacts} == {
        "model",
        "evaluation",
        "summary",
    }
    assert all(artifact.uri.startswith("file://") for artifact in result.artifacts)


def test_local_example_training_runner_requires_explicit_example_selector(
    tmp_path: Path,
) -> None:
    runner = LocalExampleTrainingRunner(tmp_path)

    assert not runner.can_run(
        _training_run(
            algorithm="xgboost",
            objective_metric_name="auc",
            hyperparameters={},
        )
    )


def _training_run(
    *,
    algorithm: str,
    objective_metric_name: str,
    hyperparameters: dict[str, object],
) -> TrainingRun:
    return TrainingRun(
        id=uuid4(),
        organization_id=uuid4(),
        project_id=uuid4(),
        experiment_id=uuid4(),
        experiment_run_id=uuid4(),
        dataset_version_id=uuid4(),
        feature_set_id=None,
        algorithm=algorithm,
        model_type=algorithm,
        objective_metric_name=objective_metric_name,
        hyperparameters=hyperparameters,
        status=TrainingRunStatus.QUEUED,
        requested_by=uuid4(),
        artifact_uri="s3://forgeml-artifacts/training-runs/run-1",
        orchestrator_run_id="local-training:run-1",
        metrics={},
        error_message=None,
    )
