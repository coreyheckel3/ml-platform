from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from forgeml.modules.auth.infrastructure.sqlalchemy_models import UserModel
from forgeml.modules.experiments.domain.entities import (
    Experiment,
    ExperimentArtifact,
    ExperimentRun,
    ExperimentRunStatus,
    ExperimentStatus,
)
from forgeml.modules.experiments.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyExperimentRepository,
)
from forgeml.modules.projects.infrastructure.sqlalchemy_models import (
    OrganizationModel,
    ProjectModel,
)
from forgeml.platform.database.base import Base


def test_experiment_repository_round_trips_experiment_runs_and_artifacts() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    experiment_id = uuid4()
    run_id = uuid4()

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
        repository = SqlAlchemyExperimentRepository(session)
        experiment = repository.add_experiment(
            Experiment(
                id=experiment_id,
                organization_id=organization_id,
                project_id=project_id,
                name="Fraud Risk Baseline",
                slug="fraud-risk-baseline",
                description="Baseline fraud models.",
                owner_user_id=user_id,
                status=ExperimentStatus.ACTIVE,
            )
        )
        run = repository.add_run(
            ExperimentRun(
                id=run_id,
                experiment_id=experiment.id,
                project_id=project_id,
                run_name="xgb-depth-6",
                status=ExperimentRunStatus.RUNNING,
                model_type="xgboost",
                started_by=user_id,
                dataset_version_id=None,
                feature_set_id=None,
                parameters={"max_depth": 6},
                metrics={},
                artifact_uri="s3://forgeml/experiments/run-1",
                evaluation_report={},
                error_message=None,
            )
        )
        repository.update_run(
            ExperimentRun(
                id=run.id,
                experiment_id=run.experiment_id,
                project_id=project_id,
                run_name=run.run_name,
                status=ExperimentRunStatus.SUCCEEDED,
                model_type=run.model_type,
                started_by=user_id,
                dataset_version_id=None,
                feature_set_id=None,
                parameters=run.parameters,
                metrics={"auc": 0.94},
                artifact_uri=run.artifact_uri,
                evaluation_report={"threshold": 0.71},
                error_message=None,
            )
        )
        repository.add_artifact(
            ExperimentArtifact(
                id=uuid4(),
                experiment_run_id=run.id,
                name="model",
                artifact_type="pickle",
                uri="s3://forgeml/experiments/run-1/model.pkl",
                metadata={"sha256": "abc"},
            )
        )
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyExperimentRepository(session)

        experiments = repository.list_experiments(organization_id, project_id)
        runs = repository.list_runs(experiment_id)
        artifacts = repository.list_artifacts(run_id)

    assert experiments[0].slug == "fraud-risk-baseline"
    assert runs[0].status == ExperimentRunStatus.SUCCEEDED
    assert runs[0].metrics["auc"] == 0.94
    assert artifacts[0].metadata["sha256"] == "abc"
