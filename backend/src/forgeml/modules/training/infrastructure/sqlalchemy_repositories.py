from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from forgeml.modules.datasets.infrastructure.sqlalchemy_models import (
    DatasetModel,
    DatasetVersionModel,
)
from forgeml.modules.experiments.domain.entities import ExperimentRun, ExperimentRunStatus
from forgeml.modules.experiments.infrastructure.sqlalchemy_models import (
    ExperimentModel,
    ExperimentRunModel,
)
from forgeml.modules.feature_store.infrastructure.sqlalchemy_models import FeatureSetModel
from forgeml.modules.projects.infrastructure.sqlalchemy_models import ProjectModel
from forgeml.modules.training.domain.entities import (
    TrainingRun,
    TrainingRunEvent,
    TrainingRunLog,
    TrainingRunStatus,
)
from forgeml.modules.training.infrastructure.sqlalchemy_models import (
    TrainingRunEventModel,
    TrainingRunLogModel,
    TrainingRunModel,
)

_RUNNABLE_TRAINING_STATUSES = {
    TrainingRunStatus.REQUESTED.value,
    TrainingRunStatus.QUEUED.value,
}
_SQLALCHEMY_METADATA_DEPENDENCIES = (ProjectModel,)


class SqlAlchemyTrainingRunRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_training_run(self, training_run: TrainingRun) -> TrainingRun:
        model = TrainingRunModel(
            id=training_run.id,
            organization_id=training_run.organization_id,
            project_id=training_run.project_id,
            experiment_id=training_run.experiment_id,
            experiment_run_id=training_run.experiment_run_id,
            dataset_version_id=training_run.dataset_version_id,
            feature_set_id=training_run.feature_set_id,
            algorithm=training_run.algorithm,
            model_type=training_run.model_type,
            objective_metric_name=training_run.objective_metric_name,
            hyperparameters_json=training_run.hyperparameters,
            status=training_run.status.value,
            requested_by=training_run.requested_by,
            artifact_uri=training_run.artifact_uri,
            orchestrator_run_id=training_run.orchestrator_run_id,
            metrics_json=training_run.metrics,
            error_message=training_run.error_message,
            attempt_count=training_run.attempt_count,
            max_attempts=training_run.max_attempts,
            worker_id=training_run.worker_id,
            lease_expires_at=training_run.lease_expires_at,
            last_heartbeat_at=training_run.last_heartbeat_at,
            queued_at=training_run.queued_at,
            started_at=training_run.started_at,
            completed_at=training_run.completed_at,
            next_retry_at=training_run.next_retry_at,
        )
        self._session.add(model)
        self._session.flush()
        return _training_run_to_domain(model)

    def get_training_run(self, training_run_id: UUID) -> TrainingRun | None:
        model = self._session.get(TrainingRunModel, training_run_id)
        return _training_run_to_domain(model) if model else None

    def list_training_runs(self, organization_id: UUID, project_id: UUID) -> list[TrainingRun]:
        models = self._session.scalars(
            select(TrainingRunModel)
            .where(
                TrainingRunModel.organization_id == organization_id,
                TrainingRunModel.project_id == project_id,
            )
            .order_by(TrainingRunModel.created_at.desc())
        ).all()
        return [_training_run_to_domain(model) for model in models]

    def list_runnable_training_runs(
        self,
        organization_id: UUID,
        project_id: UUID | None,
        limit: int,
        now: datetime,
    ) -> list[TrainingRun]:
        query = select(TrainingRunModel).where(
            TrainingRunModel.organization_id == organization_id,
            TrainingRunModel.status.in_(_RUNNABLE_TRAINING_STATUSES),
            or_(
                TrainingRunModel.next_retry_at.is_(None),
                TrainingRunModel.next_retry_at <= now,
            ),
        )
        if project_id is not None:
            query = query.where(TrainingRunModel.project_id == project_id)
        models = self._session.scalars(
            query.order_by(TrainingRunModel.created_at).limit(limit)
        ).all()
        return [_training_run_to_domain(model) for model in models]

    def list_expired_running_training_runs(
        self,
        organization_id: UUID,
        project_id: UUID | None,
        limit: int,
        now: datetime,
    ) -> list[TrainingRun]:
        query = select(TrainingRunModel).where(
            TrainingRunModel.organization_id == organization_id,
            TrainingRunModel.status == TrainingRunStatus.RUNNING.value,
            TrainingRunModel.lease_expires_at.is_not(None),
            TrainingRunModel.lease_expires_at <= now,
        )
        if project_id is not None:
            query = query.where(TrainingRunModel.project_id == project_id)
        models = self._session.scalars(
            query.order_by(TrainingRunModel.lease_expires_at).limit(limit)
        ).all()
        return [_training_run_to_domain(model) for model in models]

    def claim_training_run(
        self,
        training_run_id: UUID,
        *,
        worker_id: str,
        lease_expires_at: datetime,
        heartbeat_at: datetime,
    ) -> TrainingRun | None:
        model = self._session.scalar(
            select(TrainingRunModel)
            .where(TrainingRunModel.id == training_run_id)
            .with_for_update()
        )
        if model is None or model.status not in _RUNNABLE_TRAINING_STATUSES:
            return None
        if model.next_retry_at is not None and _is_after(model.next_retry_at, heartbeat_at):
            return None
        model.status = TrainingRunStatus.RUNNING.value
        model.worker_id = worker_id
        model.lease_expires_at = lease_expires_at
        model.last_heartbeat_at = heartbeat_at
        model.started_at = heartbeat_at
        model.completed_at = None
        model.next_retry_at = None
        model.attempt_count = int(model.attempt_count or 0) + 1
        self._session.flush()
        return _training_run_to_domain(model)

    def heartbeat_training_run(
        self,
        training_run_id: UUID,
        *,
        worker_id: str,
        lease_expires_at: datetime,
        heartbeat_at: datetime,
    ) -> TrainingRun | None:
        model = self._session.scalar(
            select(TrainingRunModel)
            .where(TrainingRunModel.id == training_run_id)
            .with_for_update()
        )
        if (
            model is None
            or model.status != TrainingRunStatus.RUNNING.value
            or model.worker_id != worker_id
        ):
            return None
        model.lease_expires_at = lease_expires_at
        model.last_heartbeat_at = heartbeat_at
        self._session.flush()
        return _training_run_to_domain(model)

    def update_training_run(self, training_run: TrainingRun) -> TrainingRun:
        model = self._session.get(TrainingRunModel, training_run.id)
        if model is None:
            raise ValueError("Training run does not exist.")
        model.status = training_run.status.value
        model.metrics_json = training_run.metrics
        model.error_message = training_run.error_message
        model.attempt_count = training_run.attempt_count
        model.max_attempts = training_run.max_attempts
        model.worker_id = training_run.worker_id
        model.lease_expires_at = training_run.lease_expires_at
        model.last_heartbeat_at = training_run.last_heartbeat_at
        model.queued_at = training_run.queued_at
        model.started_at = training_run.started_at
        model.completed_at = training_run.completed_at
        model.next_retry_at = training_run.next_retry_at
        self._session.flush()
        return _training_run_to_domain(model)

    def add_event(self, event: TrainingRunEvent) -> TrainingRunEvent:
        model = TrainingRunEventModel(
            id=event.id,
            training_run_id=event.training_run_id,
            event_type=event.event_type,
            message=event.message,
            metadata_json=event.metadata,
        )
        self._session.add(model)
        self._session.flush()
        return _event_to_domain(model)

    def list_events(self, training_run_id: UUID) -> list[TrainingRunEvent]:
        models = self._session.scalars(
            select(TrainingRunEventModel)
            .where(TrainingRunEventModel.training_run_id == training_run_id)
            .order_by(TrainingRunEventModel.created_at)
        ).all()
        return [_event_to_domain(model) for model in models]

    def add_log(self, log: TrainingRunLog) -> TrainingRunLog:
        model = TrainingRunLogModel(
            id=log.id,
            training_run_id=log.training_run_id,
            sequence=log.sequence,
            level=log.level,
            logger=log.logger,
            message=log.message,
            metadata_json=log.metadata,
        )
        self._session.add(model)
        self._session.flush()
        return _log_to_domain(model)

    def next_log_sequence(self, training_run_id: UUID) -> int:
        current_max = self._session.scalar(
            select(func.max(TrainingRunLogModel.sequence)).where(
                TrainingRunLogModel.training_run_id == training_run_id
            )
        )
        return int(current_max or 0) + 1

    def list_logs(self, training_run_id: UUID) -> list[TrainingRunLog]:
        models = self._session.scalars(
            select(TrainingRunLogModel)
            .where(TrainingRunLogModel.training_run_id == training_run_id)
            .order_by(TrainingRunLogModel.sequence)
        ).all()
        return [_log_to_domain(model) for model in models]

    def experiment_belongs_to_project(
        self,
        organization_id: UUID,
        project_id: UUID,
        experiment_id: UUID,
    ) -> bool:
        return (
            self._session.scalar(
                select(ExperimentModel.id).where(
                    ExperimentModel.id == experiment_id,
                    ExperimentModel.organization_id == organization_id,
                    ExperimentModel.project_id == project_id,
                )
            )
            is not None
        )

    def dataset_version_belongs_to_project(self, project_id: UUID, version_id: UUID) -> bool:
        return (
            self._session.scalar(
                select(DatasetVersionModel.id)
                .join(DatasetModel, DatasetModel.id == DatasetVersionModel.dataset_id)
                .where(
                    DatasetVersionModel.id == version_id,
                    DatasetModel.project_id == project_id,
                )
            )
            is not None
        )

    def feature_set_belongs_to_project(self, project_id: UUID, feature_set_id: UUID) -> bool:
        return (
            self._session.scalar(
                select(FeatureSetModel.id).where(
                    FeatureSetModel.id == feature_set_id,
                    FeatureSetModel.project_id == project_id,
                )
            )
            is not None
        )


class SqlAlchemyExperimentRunRecorder:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_experiment_run(self, run: ExperimentRun) -> ExperimentRun:
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
        return _experiment_run_to_domain(model)

    def get_experiment_run(self, run_id: UUID) -> ExperimentRun | None:
        model = self._session.get(ExperimentRunModel, run_id)
        return _experiment_run_to_domain(model) if model else None

    def update_experiment_run(
        self,
        run_id: UUID,
        status: ExperimentRunStatus,
        metrics: dict[str, float],
        evaluation_report: dict[str, object],
        error_message: str | None,
    ) -> ExperimentRun:
        model = self._session.get(ExperimentRunModel, run_id)
        if model is None:
            raise ValueError("Experiment run does not exist.")
        model.status = status.value
        model.metrics_json = metrics
        model.evaluation_report_json = evaluation_report
        model.error_message = error_message
        self._session.flush()
        return _experiment_run_to_domain(model)


def _training_run_to_domain(model: TrainingRunModel) -> TrainingRun:
    return TrainingRun(
        id=model.id,
        organization_id=model.organization_id,
        project_id=model.project_id,
        experiment_id=model.experiment_id,
        experiment_run_id=model.experiment_run_id,
        dataset_version_id=model.dataset_version_id,
        feature_set_id=model.feature_set_id,
        algorithm=model.algorithm,
        model_type=model.model_type,
        objective_metric_name=model.objective_metric_name,
        hyperparameters=model.hyperparameters_json,
        status=TrainingRunStatus(model.status),
        requested_by=model.requested_by,
        artifact_uri=model.artifact_uri,
        orchestrator_run_id=model.orchestrator_run_id,
        metrics={key: float(value) for key, value in model.metrics_json.items()},
        error_message=model.error_message,
        attempt_count=model.attempt_count,
        max_attempts=model.max_attempts,
        worker_id=model.worker_id,
        lease_expires_at=model.lease_expires_at,
        last_heartbeat_at=model.last_heartbeat_at,
        queued_at=model.queued_at,
        started_at=model.started_at,
        completed_at=model.completed_at,
        next_retry_at=model.next_retry_at,
    )


def _experiment_run_to_domain(model: ExperimentRunModel) -> ExperimentRun:
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


def _event_to_domain(model: TrainingRunEventModel) -> TrainingRunEvent:
    return TrainingRunEvent(
        id=model.id,
        training_run_id=model.training_run_id,
        event_type=model.event_type,
        message=model.message,
        metadata=model.metadata_json,
    )


def _log_to_domain(model: TrainingRunLogModel) -> TrainingRunLog:
    return TrainingRunLog(
        id=model.id,
        training_run_id=model.training_run_id,
        sequence=model.sequence,
        level=model.level,
        logger=model.logger,
        message=model.message,
        metadata=model.metadata_json,
        created_at=model.created_at,
    )


def _is_after(value: datetime, reference: datetime) -> bool:
    if value.tzinfo is None and reference.tzinfo is not None:
        return value.replace(tzinfo=reference.tzinfo) > reference
    if value.tzinfo is not None and reference.tzinfo is None:
        return value > reference.replace(tzinfo=value.tzinfo)
    return value > reference
