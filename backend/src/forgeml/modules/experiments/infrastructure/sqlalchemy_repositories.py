from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from forgeml.modules.experiments.domain.entities import (
    Experiment,
    ExperimentArtifact,
    ExperimentRun,
    ExperimentRunStatus,
    ExperimentStatus,
)
from forgeml.modules.experiments.infrastructure.sqlalchemy_models import (
    ExperimentArtifactModel,
    ExperimentModel,
    ExperimentRunModel,
)


class SqlAlchemyExperimentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_experiment(self, experiment: Experiment) -> Experiment:
        model = ExperimentModel(
            id=experiment.id,
            organization_id=experiment.organization_id,
            project_id=experiment.project_id,
            name=experiment.name,
            slug=experiment.slug,
            description=experiment.description,
            owner_user_id=experiment.owner_user_id,
            status=experiment.status.value,
        )
        self._session.add(model)
        self._session.flush()
        return _experiment_to_domain(model)

    def get_experiment(self, experiment_id: UUID) -> Experiment | None:
        model = self._session.get(ExperimentModel, experiment_id)
        return _experiment_to_domain(model) if model else None

    def list_experiments(self, organization_id: UUID, project_id: UUID) -> list[Experiment]:
        models = self._session.scalars(
            select(ExperimentModel)
            .where(
                ExperimentModel.organization_id == organization_id,
                ExperimentModel.project_id == project_id,
            )
            .order_by(ExperimentModel.name)
        ).all()
        return [_experiment_to_domain(model) for model in models]

    def experiment_slug_exists(self, organization_id: UUID, project_id: UUID, slug: str) -> bool:
        return (
            self._session.scalar(
                select(ExperimentModel.id).where(
                    ExperimentModel.organization_id == organization_id,
                    ExperimentModel.project_id == project_id,
                    ExperimentModel.slug == slug,
                )
            )
            is not None
        )

    def add_run(self, run: ExperimentRun) -> ExperimentRun:
        model = ExperimentRunModel(
            id=run.id,
            experiment_id=run.experiment_id,
            project_id=run.project_id,
            run_name=run.run_name,
            status=run.status.value,
            model_type=run.model_type,
            started_by=run.started_by,
            dataset_version_id=run.dataset_version_id,
            feature_set_id=run.feature_set_id,
            parameters_json=run.parameters,
            metrics_json=run.metrics,
            artifact_uri=run.artifact_uri,
            evaluation_report_json=run.evaluation_report,
            error_message=run.error_message,
        )
        self._session.add(model)
        self._session.flush()
        return _run_to_domain(model)

    def get_run(self, run_id: UUID) -> ExperimentRun | None:
        model = self._session.get(ExperimentRunModel, run_id)
        return _run_to_domain(model) if model else None

    def list_runs(self, experiment_id: UUID) -> list[ExperimentRun]:
        models = self._session.scalars(
            select(ExperimentRunModel)
            .where(ExperimentRunModel.experiment_id == experiment_id)
            .order_by(ExperimentRunModel.created_at.desc())
        ).all()
        return [_run_to_domain(model) for model in models]

    def update_run(self, run: ExperimentRun) -> ExperimentRun:
        model = self._session.get(ExperimentRunModel, run.id)
        if model is None:
            raise ValueError("Experiment run does not exist.")
        model.status = run.status.value
        model.metrics_json = run.metrics
        model.evaluation_report_json = run.evaluation_report
        model.error_message = run.error_message
        self._session.flush()
        return _run_to_domain(model)

    def add_artifact(self, artifact: ExperimentArtifact) -> ExperimentArtifact:
        model = ExperimentArtifactModel(
            id=artifact.id,
            experiment_run_id=artifact.experiment_run_id,
            name=artifact.name,
            artifact_type=artifact.artifact_type,
            uri=artifact.uri,
            metadata_json=artifact.metadata,
        )
        self._session.add(model)
        self._session.flush()
        return _artifact_to_domain(model)

    def list_artifacts(self, experiment_run_id: UUID) -> list[ExperimentArtifact]:
        models = self._session.scalars(
            select(ExperimentArtifactModel)
            .where(ExperimentArtifactModel.experiment_run_id == experiment_run_id)
            .order_by(ExperimentArtifactModel.name)
        ).all()
        return [_artifact_to_domain(model) for model in models]


def _experiment_to_domain(model: ExperimentModel) -> Experiment:
    return Experiment(
        id=model.id,
        organization_id=model.organization_id,
        project_id=model.project_id,
        name=model.name,
        slug=model.slug,
        description=model.description,
        owner_user_id=model.owner_user_id,
        status=ExperimentStatus(model.status),
    )


def _run_to_domain(model: ExperimentRunModel) -> ExperimentRun:
    return ExperimentRun(
        id=model.id,
        experiment_id=model.experiment_id,
        project_id=model.project_id,
        run_name=model.run_name,
        status=ExperimentRunStatus(model.status),
        model_type=model.model_type,
        started_by=model.started_by,
        dataset_version_id=model.dataset_version_id,
        feature_set_id=model.feature_set_id,
        parameters=model.parameters_json,
        metrics={key: float(value) for key, value in model.metrics_json.items()},
        artifact_uri=model.artifact_uri,
        evaluation_report=model.evaluation_report_json,
        error_message=model.error_message,
    )


def _artifact_to_domain(model: ExperimentArtifactModel) -> ExperimentArtifact:
    return ExperimentArtifact(
        id=model.id,
        experiment_run_id=model.experiment_run_id,
        name=model.name,
        artifact_type=model.artifact_type,
        uri=model.uri,
        metadata=model.metadata_json,
    )
