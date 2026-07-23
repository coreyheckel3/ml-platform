from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from forgeml.modules.alerting.infrastructure.sqlalchemy_models import AlertEventModel
from forgeml.modules.datasets.infrastructure.sqlalchemy_models import (
    DatasetModel,
    DatasetVersionModel,
)
from forgeml.modules.deployments.infrastructure.sqlalchemy_models import DeploymentModel
from forgeml.modules.drift_detection.infrastructure.sqlalchemy_models import DriftReportModel
from forgeml.modules.experiments.infrastructure.sqlalchemy_models import ExperimentModel
from forgeml.modules.feature_store.infrastructure.sqlalchemy_models import FeatureSetModel
from forgeml.modules.inference.infrastructure.sqlalchemy_models import InferenceEndpointModel
from forgeml.modules.retraining.domain.entities import (
    AlertRetrainingSignal,
    DriftRetrainingSignal,
    RetrainingPolicy,
    RetrainingPolicyStatus,
    RetrainingRun,
    RetrainingRunStatus,
    RetrainingTriggerType,
)
from forgeml.modules.retraining.infrastructure.sqlalchemy_models import (
    RetrainingPolicyModel,
    RetrainingRunModel,
)

_ACTIVE_RETRAINING_STATUSES = (
    RetrainingRunStatus.PENDING_APPROVAL.value,
    RetrainingRunStatus.QUEUED.value,
    RetrainingRunStatus.FAILED.value,
)


class SqlAlchemyRetrainingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_policy(self, policy: RetrainingPolicy) -> RetrainingPolicy:
        model = RetrainingPolicyModel(
            id=policy.id,
            organization_id=policy.organization_id,
            project_id=policy.project_id,
            deployment_id=policy.deployment_id,
            name=policy.name,
            slug=policy.slug,
            description=policy.description,
            trigger_type=policy.trigger_type.value,
            trigger_config_json=policy.trigger_config,
            training_template_json=policy.training_template,
            cooldown_seconds=policy.cooldown_seconds,
            max_runs_per_day=policy.max_runs_per_day,
            approval_required=policy.approval_required,
            enabled=policy.enabled,
            status=policy.status.value,
            created_by=policy.created_by,
        )
        self._session.add(model)
        self._session.flush()
        return _policy_to_domain(model)

    def get_policy(self, policy_id: UUID) -> RetrainingPolicy | None:
        model = self._session.get(RetrainingPolicyModel, policy_id)
        return _policy_to_domain(model) if model else None

    def list_policies(self, organization_id: UUID, project_id: UUID) -> list[RetrainingPolicy]:
        models = self._session.scalars(
            select(RetrainingPolicyModel)
            .where(
                RetrainingPolicyModel.organization_id == organization_id,
                RetrainingPolicyModel.project_id == project_id,
            )
            .order_by(RetrainingPolicyModel.name)
        ).all()
        return [_policy_to_domain(model) for model in models]

    def policy_slug_exists(
        self,
        organization_id: UUID,
        project_id: UUID,
        slug: str,
    ) -> bool:
        return (
            self._session.scalar(
                select(RetrainingPolicyModel.id).where(
                    RetrainingPolicyModel.organization_id == organization_id,
                    RetrainingPolicyModel.project_id == project_id,
                    RetrainingPolicyModel.slug == slug,
                )
            )
            is not None
        )

    def add_run(self, run: RetrainingRun) -> RetrainingRun:
        model = RetrainingRunModel(
            id=run.id,
            organization_id=run.organization_id,
            project_id=run.project_id,
            policy_id=run.policy_id,
            deployment_id=run.deployment_id,
            trigger_type=run.trigger_type.value,
            drift_report_id=run.drift_report_id,
            alert_event_id=run.alert_event_id,
            training_run_id=run.training_run_id,
            status=run.status.value,
            reason=run.reason,
            training_config_json=run.training_config,
            decision_metadata_json=run.decision_metadata,
            requested_by=run.requested_by,
            approved_by=run.approved_by,
            rejected_by=run.rejected_by,
        )
        self._session.add(model)
        self._session.flush()
        return _run_to_domain(model)

    def get_run(self, run_id: UUID) -> RetrainingRun | None:
        model = self._session.get(RetrainingRunModel, run_id)
        return _run_to_domain(model) if model else None

    def update_run(self, run: RetrainingRun) -> RetrainingRun:
        model = self._session.get(RetrainingRunModel, run.id)
        if model is None:
            raise ValueError("Retraining run does not exist.")
        model.training_run_id = run.training_run_id
        model.status = run.status.value
        model.reason = run.reason
        model.training_config_json = run.training_config
        model.decision_metadata_json = run.decision_metadata
        model.approved_by = run.approved_by
        model.rejected_by = run.rejected_by
        self._session.flush()
        return _run_to_domain(model)

    def list_runs(self, organization_id: UUID, project_id: UUID) -> list[RetrainingRun]:
        models = self._session.scalars(
            select(RetrainingRunModel)
            .where(
                RetrainingRunModel.organization_id == organization_id,
                RetrainingRunModel.project_id == project_id,
            )
            .order_by(RetrainingRunModel.created_at.desc())
        ).all()
        return [_run_to_domain(model) for model in models]

    def get_existing_run_for_trigger(
        self,
        policy_id: UUID,
        drift_report_id: UUID | None,
        alert_event_id: UUID | None,
    ) -> RetrainingRun | None:
        statement = select(RetrainingRunModel).where(RetrainingRunModel.policy_id == policy_id)
        if drift_report_id is not None:
            statement = statement.where(RetrainingRunModel.drift_report_id == drift_report_id)
        elif alert_event_id is not None:
            statement = statement.where(RetrainingRunModel.alert_event_id == alert_event_id)
        else:
            return None
        model = self._session.scalars(
            statement.order_by(RetrainingRunModel.created_at.desc())
        ).first()
        return _run_to_domain(model) if model else None

    def latest_run_created_at(self, policy_id: UUID) -> datetime | None:
        return self._session.scalar(
            select(RetrainingRunModel.created_at)
            .where(
                RetrainingRunModel.policy_id == policy_id,
                RetrainingRunModel.status.in_(_ACTIVE_RETRAINING_STATUSES),
            )
            .order_by(RetrainingRunModel.created_at.desc())
        )

    def count_runs_since(self, policy_id: UUID, since: datetime) -> int:
        count = self._session.scalar(
            select(func.count(RetrainingRunModel.id)).where(
                RetrainingRunModel.policy_id == policy_id,
                RetrainingRunModel.status.in_(_ACTIVE_RETRAINING_STATUSES),
                RetrainingRunModel.created_at >= since,
            )
        )
        return int(count or 0)

    def deployment_belongs_to_project(
        self,
        organization_id: UUID,
        project_id: UUID,
        deployment_id: UUID,
    ) -> bool:
        return (
            self._session.scalar(
                select(DeploymentModel.id).where(
                    DeploymentModel.id == deployment_id,
                    DeploymentModel.organization_id == organization_id,
                    DeploymentModel.project_id == project_id,
                )
            )
            is not None
        )

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

    def get_drift_signal(self, drift_report_id: UUID) -> DriftRetrainingSignal | None:
        model = self._session.get(DriftReportModel, drift_report_id)
        if model is None:
            return None
        return DriftRetrainingSignal(
            drift_report_id=model.id,
            organization_id=model.organization_id,
            project_id=model.project_id,
            deployment_id=model.deployment_id,
            endpoint_id=model.endpoint_id,
            drift_score=float(model.drift_score),
            drifted_feature_count=model.drifted_feature_count,
            evaluated_feature_count=model.evaluated_feature_count,
            status=model.status,
            created_at=model.created_at,
        )

    def get_alert_signal(self, alert_event_id: UUID) -> AlertRetrainingSignal | None:
        row = self._session.execute(
            select(AlertEventModel, InferenceEndpointModel.deployment_id)
            .outerjoin(
                InferenceEndpointModel,
                AlertEventModel.endpoint_id == InferenceEndpointModel.id,
            )
            .where(AlertEventModel.id == alert_event_id)
        ).first()
        if row is None:
            return None
        model, deployment_id = row
        return AlertRetrainingSignal(
            alert_event_id=model.id,
            organization_id=model.organization_id,
            project_id=model.project_id,
            endpoint_id=model.endpoint_id,
            deployment_id=deployment_id,
            severity=model.severity,
            status=model.status,
            observed_value=float(model.observed_value),
            threshold=float(model.threshold),
            metadata=model.metadata_json,
            created_at=model.triggered_at,
        )


def _policy_to_domain(model: RetrainingPolicyModel) -> RetrainingPolicy:
    return RetrainingPolicy(
        id=model.id,
        organization_id=model.organization_id,
        project_id=model.project_id,
        deployment_id=model.deployment_id,
        name=model.name,
        slug=model.slug,
        description=model.description,
        trigger_type=RetrainingTriggerType(model.trigger_type),
        trigger_config=model.trigger_config_json,
        training_template=model.training_template_json,
        cooldown_seconds=model.cooldown_seconds,
        max_runs_per_day=model.max_runs_per_day,
        approval_required=model.approval_required,
        enabled=model.enabled,
        status=RetrainingPolicyStatus(model.status),
        created_by=model.created_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _run_to_domain(model: RetrainingRunModel) -> RetrainingRun:
    return RetrainingRun(
        id=model.id,
        organization_id=model.organization_id,
        project_id=model.project_id,
        policy_id=model.policy_id,
        deployment_id=model.deployment_id,
        trigger_type=RetrainingTriggerType(model.trigger_type),
        drift_report_id=model.drift_report_id,
        alert_event_id=model.alert_event_id,
        training_run_id=model.training_run_id,
        status=RetrainingRunStatus(model.status),
        reason=model.reason,
        training_config=model.training_config_json,
        decision_metadata=model.decision_metadata_json,
        requested_by=model.requested_by,
        approved_by=model.approved_by,
        rejected_by=model.rejected_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
