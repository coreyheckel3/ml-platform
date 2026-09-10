from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from forgeml.modules.alerting.infrastructure.sqlalchemy_models import (
    AlertEventModel,
    AlertRuleModel,
)
from forgeml.modules.datasets.infrastructure.sqlalchemy_models import (
    DatasetModel,
    DatasetValidationRunModel,
    DatasetVersionModel,
)
from forgeml.modules.deployments.infrastructure.sqlalchemy_models import (
    DeploymentModel,
)
from forgeml.modules.drift_detection.infrastructure.sqlalchemy_models import (
    DriftProfileModel,
    DriftReportModel,
)
from forgeml.modules.experiments.infrastructure.sqlalchemy_models import (
    ExperimentModel,
    ExperimentRunModel,
)
from forgeml.modules.feature_store.infrastructure.sqlalchemy_models import (
    FeatureMaterializationModel,
    FeaturePipelineModel,
    FeatureSetModel,
)
from forgeml.modules.inference.infrastructure.sqlalchemy_models import (
    InferenceEndpointModel,
    InferenceMetricSnapshotModel,
    InferenceRequestLogModel,
)
from forgeml.modules.lifecycle.domain.entities import ProjectLifecycleSnapshot
from forgeml.modules.model_registry.infrastructure.sqlalchemy_models import (
    ModelApprovalModel,
    ModelVersionModel,
    RegisteredModelModel,
)
from forgeml.modules.projects.infrastructure.sqlalchemy_models import ProjectModel
from forgeml.modules.retraining.infrastructure.sqlalchemy_models import (
    RetrainingPolicyModel,
    RetrainingRunModel,
)
from forgeml.modules.training.infrastructure.sqlalchemy_models import TrainingRunModel


class SqlAlchemyProjectLifecycleRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def load_snapshot(
        self,
        organization_id: UUID,
        project_id: UUID,
    ) -> ProjectLifecycleSnapshot | None:
        project = self._session.scalar(
            select(ProjectModel).where(
                ProjectModel.id == project_id,
                ProjectModel.organization_id == organization_id,
            )
        )
        if project is None:
            return None

        dataset_ids = select(DatasetModel.id).where(
            DatasetModel.organization_id == organization_id,
            DatasetModel.project_id == project_id,
        )
        feature_set_ids = select(FeatureSetModel.id).where(
            FeatureSetModel.organization_id == organization_id,
            FeatureSetModel.project_id == project_id,
        )
        experiment_ids = select(ExperimentModel.id).where(
            ExperimentModel.organization_id == organization_id,
            ExperimentModel.project_id == project_id,
        )
        registered_model_ids = select(RegisteredModelModel.id).where(
            RegisteredModelModel.organization_id == organization_id,
            RegisteredModelModel.project_id == project_id,
        )
        endpoint_ids = select(InferenceEndpointModel.id).where(
            InferenceEndpointModel.organization_id == organization_id,
            InferenceEndpointModel.project_id == project_id,
        )

        inference_metrics = self._session.execute(
            select(
                func.coalesce(func.sum(InferenceMetricSnapshotModel.prediction_count), 0),
                func.coalesce(func.sum(InferenceMetricSnapshotModel.error_count), 0),
                func.coalesce(func.max(InferenceMetricSnapshotModel.p95_latency_ms), 0.0),
            ).where(InferenceMetricSnapshotModel.endpoint_id.in_(endpoint_ids))
        ).one()

        return ProjectLifecycleSnapshot(
            project_id=project.id,
            project_name=project.name,
            project_slug=project.slug,
            project_status=project.status,
            datasets=_count(
                self._session,
                DatasetModel.id,
                DatasetModel.organization_id == organization_id,
                DatasetModel.project_id == project_id,
            ),
            dataset_versions=_count(
                self._session,
                DatasetVersionModel.id,
                DatasetVersionModel.dataset_id.in_(dataset_ids),
            ),
            validation_runs=_count(
                self._session,
                DatasetValidationRunModel.id,
                DatasetValidationRunModel.dataset_version_id.in_(
                    select(DatasetVersionModel.id).where(
                        DatasetVersionModel.dataset_id.in_(dataset_ids)
                    )
                ),
            ),
            feature_sets=_count(
                self._session,
                FeatureSetModel.id,
                FeatureSetModel.organization_id == organization_id,
                FeatureSetModel.project_id == project_id,
            ),
            feature_pipelines=_count(
                self._session,
                FeaturePipelineModel.id,
                FeaturePipelineModel.feature_set_id.in_(feature_set_ids),
            ),
            materializations=_count(
                self._session,
                FeatureMaterializationModel.id,
                FeatureMaterializationModel.feature_set_id.in_(feature_set_ids),
            ),
            experiments=_count(
                self._session,
                ExperimentModel.id,
                ExperimentModel.organization_id == organization_id,
                ExperimentModel.project_id == project_id,
            ),
            experiment_runs=_count(
                self._session,
                ExperimentRunModel.id,
                ExperimentRunModel.project_id == project_id,
                ExperimentRunModel.experiment_id.in_(experiment_ids),
            ),
            training_runs=_count_training_runs(self._session, organization_id, project_id),
            succeeded_training_runs=_count_training_runs(
                self._session,
                organization_id,
                project_id,
                ("succeeded",),
            ),
            failed_training_runs=_count_training_runs(
                self._session,
                organization_id,
                project_id,
                ("failed", "dead_lettered"),
            ),
            registered_models=_count(
                self._session,
                RegisteredModelModel.id,
                RegisteredModelModel.organization_id == organization_id,
                RegisteredModelModel.project_id == project_id,
            ),
            model_versions=_count(
                self._session,
                ModelVersionModel.id,
                ModelVersionModel.registered_model_id.in_(registered_model_ids),
            ),
            approved_model_versions=_count_distinct(
                self._session,
                ModelApprovalModel.model_version_id,
                ModelApprovalModel.model_version_id.in_(
                    select(ModelVersionModel.id).where(
                        ModelVersionModel.registered_model_id.in_(registered_model_ids)
                    )
                ),
                ModelApprovalModel.status == "approved",
            ),
            deployments=_count(
                self._session,
                DeploymentModel.id,
                DeploymentModel.organization_id == organization_id,
                DeploymentModel.project_id == project_id,
            ),
            active_deployments=_count(
                self._session,
                DeploymentModel.id,
                DeploymentModel.organization_id == organization_id,
                DeploymentModel.project_id == project_id,
                DeploymentModel.status == "active",
            ),
            inference_endpoints=_count(
                self._session,
                InferenceEndpointModel.id,
                InferenceEndpointModel.organization_id == organization_id,
                InferenceEndpointModel.project_id == project_id,
            ),
            active_inference_endpoints=_count(
                self._session,
                InferenceEndpointModel.id,
                InferenceEndpointModel.organization_id == organization_id,
                InferenceEndpointModel.project_id == project_id,
                InferenceEndpointModel.status == "active",
            ),
            prediction_count=int(inference_metrics[0] or 0),
            request_count=_count(
                self._session,
                InferenceRequestLogModel.id,
                InferenceRequestLogModel.endpoint_id.in_(endpoint_ids),
            ),
            inference_error_count=int(inference_metrics[1] or 0),
            max_p95_latency_ms=float(inference_metrics[2] or 0.0),
            drift_profiles=_count(
                self._session,
                DriftProfileModel.id,
                DriftProfileModel.organization_id == organization_id,
                DriftProfileModel.project_id == project_id,
            ),
            drift_reports=_count(
                self._session,
                DriftReportModel.id,
                DriftReportModel.organization_id == organization_id,
                DriftReportModel.project_id == project_id,
            ),
            breached_drift_reports=_count(
                self._session,
                DriftReportModel.id,
                DriftReportModel.organization_id == organization_id,
                DriftReportModel.project_id == project_id,
                DriftReportModel.status == "completed",
                DriftReportModel.drift_score >= DriftReportModel.drift_threshold,
            ),
            alert_rules=_count(
                self._session,
                AlertRuleModel.id,
                AlertRuleModel.organization_id == organization_id,
                AlertRuleModel.project_id == project_id,
            ),
            active_alert_events=_count(
                self._session,
                AlertEventModel.id,
                AlertEventModel.organization_id == organization_id,
                AlertEventModel.project_id == project_id,
                AlertEventModel.status.in_(("open", "acknowledged")),
            ),
            retraining_policies=_count(
                self._session,
                RetrainingPolicyModel.id,
                RetrainingPolicyModel.organization_id == organization_id,
                RetrainingPolicyModel.project_id == project_id,
            ),
            enabled_retraining_policies=_count(
                self._session,
                RetrainingPolicyModel.id,
                RetrainingPolicyModel.organization_id == organization_id,
                RetrainingPolicyModel.project_id == project_id,
                RetrainingPolicyModel.status == "active",
                RetrainingPolicyModel.enabled.is_(True),
            ),
            retraining_runs=_count(
                self._session,
                RetrainingRunModel.id,
                RetrainingRunModel.organization_id == organization_id,
                RetrainingRunModel.project_id == project_id,
            ),
            successful_retraining_runs=_count(
                self._session,
                RetrainingRunModel.id,
                RetrainingRunModel.organization_id == organization_id,
                RetrainingRunModel.project_id == project_id,
                RetrainingRunModel.status == "succeeded",
            ),
            queued_retraining_runs=_count(
                self._session,
                RetrainingRunModel.id,
                RetrainingRunModel.organization_id == organization_id,
                RetrainingRunModel.project_id == project_id,
                RetrainingRunModel.status.in_(("queued", "pending_approval", "running")),
            ),
            last_updated_at=_latest_project_update(self._session, organization_id, project_id),
        )


def _count(session: Session, column, *conditions) -> int:  # noqa: ANN001
    return int(session.scalar(select(func.count(column)).where(*conditions)) or 0)


def _count_distinct(session: Session, column, *conditions) -> int:  # noqa: ANN001
    return int(
        session.scalar(select(func.count(func.distinct(column))).where(*conditions))
        or 0
    )


def _count_training_runs(
    session: Session,
    organization_id: UUID,
    project_id: UUID,
    statuses: tuple[str, ...] | None = None,
) -> int:
    conditions = [
        TrainingRunModel.organization_id == organization_id,
        TrainingRunModel.project_id == project_id,
    ]
    if statuses is not None:
        conditions.append(TrainingRunModel.status.in_(statuses))
    return _count(session, TrainingRunModel.id, *conditions)


def _latest_project_update(
    session: Session,
    organization_id: UUID,
    project_id: UUID,
) -> datetime | None:
    timestamps = (
        session.scalar(
            select(func.max(DatasetModel.updated_at)).where(
                DatasetModel.organization_id == organization_id,
                DatasetModel.project_id == project_id,
            )
        ),
        session.scalar(
            select(func.max(FeatureSetModel.updated_at)).where(
                FeatureSetModel.organization_id == organization_id,
                FeatureSetModel.project_id == project_id,
            )
        ),
        session.scalar(
            select(func.max(ExperimentRunModel.updated_at)).where(
                ExperimentRunModel.project_id == project_id,
                ExperimentRunModel.experiment_id.in_(
                    select(ExperimentModel.id).where(
                        ExperimentModel.organization_id == organization_id,
                        ExperimentModel.project_id == project_id,
                    )
                ),
            )
        ),
        session.scalar(
            select(func.max(TrainingRunModel.updated_at)).where(
                TrainingRunModel.organization_id == organization_id,
                TrainingRunModel.project_id == project_id,
            )
        ),
        session.scalar(
            select(func.max(RegisteredModelModel.updated_at)).where(
                RegisteredModelModel.organization_id == organization_id,
                RegisteredModelModel.project_id == project_id,
            )
        ),
        session.scalar(
            select(func.max(DeploymentModel.updated_at)).where(
                DeploymentModel.organization_id == organization_id,
                DeploymentModel.project_id == project_id,
            )
        ),
        session.scalar(
            select(func.max(InferenceEndpointModel.updated_at)).where(
                InferenceEndpointModel.organization_id == organization_id,
                InferenceEndpointModel.project_id == project_id,
            )
        ),
        session.scalar(
            select(func.max(DriftReportModel.created_at)).where(
                DriftReportModel.organization_id == organization_id,
                DriftReportModel.project_id == project_id,
            )
        ),
        session.scalar(
            select(func.max(RetrainingRunModel.updated_at)).where(
                RetrainingRunModel.organization_id == organization_id,
                RetrainingRunModel.project_id == project_id,
            )
        ),
    )
    present = [timestamp for timestamp in timestamps if timestamp is not None]
    return max(present) if present else None
