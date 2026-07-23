from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from forgeml.modules.auth.infrastructure.sqlalchemy_models import UserModel
from forgeml.modules.datasets.domain.entities import (
    DatasetSourceType,
    DatasetStatus,
    DatasetVersionStatus,
)
from forgeml.modules.datasets.infrastructure.sqlalchemy_models import (
    DatasetModel,
    DatasetVersionModel,
)
from forgeml.modules.experiments.domain.entities import (
    ExperimentRun,
    ExperimentRunStatus,
    ExperimentStatus,
)
from forgeml.modules.experiments.infrastructure.sqlalchemy_models import ExperimentModel
from forgeml.modules.feature_store.domain.entities import FeatureSetStatus
from forgeml.modules.feature_store.infrastructure.sqlalchemy_models import FeatureSetModel
from forgeml.modules.projects.infrastructure.sqlalchemy_models import (
    OrganizationModel,
    ProjectModel,
)
from forgeml.modules.training.domain.entities import (
    TrainingRun,
    TrainingRunEvent,
    TrainingRunStatus,
)
from forgeml.modules.training.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyExperimentRunRecorder,
    SqlAlchemyTrainingRunRepository,
)
from forgeml.platform.database.base import Base


def test_training_repository_round_trips_training_runs_events_and_reference_checks() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    dataset_id = uuid4()
    dataset_version_id = uuid4()
    feature_set_id = uuid4()
    experiment_id = uuid4()
    experiment_run_id = uuid4()
    training_run_id = uuid4()

    with Session(engine) as session:
        session.add(OrganizationModel(id=organization_id, name="ForgeML", slug="forgeml"))
        session.add(
            UserModel(
                id=user_id,
                organization_id=organization_id,
                email="owner@example.com",
                display_name="Owner",
                password_hash="hash",
                permissions_csv="*",
            )
        )
        session.add(
            ProjectModel(
                id=project_id,
                organization_id=organization_id,
                name="Fraud",
                slug="fraud",
                owner_user_id=user_id,
            )
        )
        session.add(
            DatasetModel(
                id=dataset_id,
                organization_id=organization_id,
                project_id=project_id,
                name="Transactions",
                slug="transactions",
                description="",
                source_type=DatasetSourceType.UPLOAD.value,
                status=DatasetStatus.ACTIVE.value,
            )
        )
        session.add(
            DatasetVersionModel(
                id=dataset_version_id,
                dataset_id=dataset_id,
                version=1,
                object_uri="s3://forgeml/transactions.csv",
                content_hash="sha256:abc",
                row_count=10,
                size_bytes=128,
                status=DatasetVersionStatus.VALIDATED.value,
                created_by=user_id,
            )
        )
        session.add(
            FeatureSetModel(
                id=feature_set_id,
                organization_id=organization_id,
                project_id=project_id,
                name="Merchant Signals",
                slug="merchant-signals",
                description="",
                entity_key="merchant_id",
                status=FeatureSetStatus.ACTIVE.value,
            )
        )
        session.add(
            ExperimentModel(
                id=experiment_id,
                organization_id=organization_id,
                project_id=project_id,
                name="Fraud Risk Baseline",
                slug="fraud-risk-baseline",
                description="",
                owner_user_id=user_id,
                status=ExperimentStatus.ACTIVE.value,
            )
        )
        recorder = SqlAlchemyExperimentRunRecorder(session)
        experiment_run = recorder.add_experiment_run(
            ExperimentRun(
                id=experiment_run_id,
                experiment_id=experiment_id,
                project_id=project_id,
                run_name="xgb-depth-6",
                status=ExperimentRunStatus.RUNNING,
                model_type="xgboost",
                started_by=user_id,
                dataset_version_id=dataset_version_id,
                feature_set_id=feature_set_id,
                parameters={"max_depth": 6},
                metrics={},
                artifact_uri="s3://forgeml/training-runs/run-1",
                evaluation_report={},
                error_message=None,
            )
        )
        repository = SqlAlchemyTrainingRunRepository(session)
        training_run = repository.add_training_run(
            TrainingRun(
                id=training_run_id,
                organization_id=organization_id,
                project_id=project_id,
                experiment_id=experiment_id,
                experiment_run_id=experiment_run.id,
                dataset_version_id=dataset_version_id,
                feature_set_id=feature_set_id,
                algorithm="xgboost",
                model_type="xgboost",
                objective_metric_name="auc",
                hyperparameters={"max_depth": 6},
                status=TrainingRunStatus.QUEUED,
                requested_by=user_id,
                artifact_uri="s3://forgeml/training-runs/run-1",
                orchestrator_run_id="workflow-1",
                metrics={},
                error_message=None,
            )
        )
        repository.update_training_run(
            TrainingRun(
                id=training_run.id,
                organization_id=organization_id,
                project_id=project_id,
                experiment_id=experiment_id,
                experiment_run_id=experiment_run.id,
                dataset_version_id=dataset_version_id,
                feature_set_id=feature_set_id,
                algorithm="xgboost",
                model_type="xgboost",
                objective_metric_name="auc",
                hyperparameters={"max_depth": 6},
                status=TrainingRunStatus.SUCCEEDED,
                requested_by=user_id,
                artifact_uri="s3://forgeml/training-runs/run-1",
                orchestrator_run_id="workflow-1",
                metrics={"auc": 0.94},
                error_message=None,
            )
        )
        repository.add_event(
            TrainingRunEvent(
                id=uuid4(),
                training_run_id=training_run.id,
                event_type="queued",
                message="Training run was queued.",
                metadata={"orchestrator_run_id": "workflow-1"},
            )
        )
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyTrainingRunRepository(session)

        training_runs = repository.list_training_runs(organization_id, project_id)
        events = repository.list_events(training_run_id)
        experiment_exists = repository.experiment_belongs_to_project(
            organization_id,
            project_id,
            experiment_id,
        )
        dataset_exists = repository.dataset_version_belongs_to_project(
            project_id,
            dataset_version_id,
        )
        feature_set_exists = repository.feature_set_belongs_to_project(project_id, feature_set_id)

    assert training_runs[0].status == TrainingRunStatus.SUCCEEDED
    assert training_runs[0].metrics["auc"] == 0.94
    assert events[0].event_type == "queued"
    assert experiment_exists
    assert dataset_exists
    assert feature_set_exists
