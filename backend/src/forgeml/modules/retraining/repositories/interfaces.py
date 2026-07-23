from datetime import datetime
from typing import Protocol
from uuid import UUID

from forgeml.modules.retraining.domain.entities import (
    AlertRetrainingSignal,
    DriftRetrainingSignal,
    RetrainingPolicy,
    RetrainingRun,
    RetrainingTrainingLaunch,
    RetrainingTrainingRequest,
)
from forgeml.platform.security.rbac import Principal


class RetrainingRepository(Protocol):
    def add_policy(self, policy: RetrainingPolicy) -> RetrainingPolicy:
        raise NotImplementedError

    def get_policy(self, policy_id: UUID) -> RetrainingPolicy | None:
        raise NotImplementedError

    def list_policies(self, organization_id: UUID, project_id: UUID) -> list[RetrainingPolicy]:
        raise NotImplementedError

    def policy_slug_exists(
        self,
        organization_id: UUID,
        project_id: UUID,
        slug: str,
    ) -> bool:
        raise NotImplementedError

    def add_run(self, run: RetrainingRun) -> RetrainingRun:
        raise NotImplementedError

    def get_run(self, run_id: UUID) -> RetrainingRun | None:
        raise NotImplementedError

    def update_run(self, run: RetrainingRun) -> RetrainingRun:
        raise NotImplementedError

    def list_runs(self, organization_id: UUID, project_id: UUID) -> list[RetrainingRun]:
        raise NotImplementedError

    def get_existing_run_for_trigger(
        self,
        policy_id: UUID,
        drift_report_id: UUID | None,
        alert_event_id: UUID | None,
    ) -> RetrainingRun | None:
        raise NotImplementedError

    def latest_run_created_at(self, policy_id: UUID) -> datetime | None:
        raise NotImplementedError

    def count_runs_since(self, policy_id: UUID, since: datetime) -> int:
        raise NotImplementedError

    def deployment_belongs_to_project(
        self,
        organization_id: UUID,
        project_id: UUID,
        deployment_id: UUID,
    ) -> bool:
        raise NotImplementedError

    def experiment_belongs_to_project(
        self,
        organization_id: UUID,
        project_id: UUID,
        experiment_id: UUID,
    ) -> bool:
        raise NotImplementedError

    def dataset_version_belongs_to_project(self, project_id: UUID, version_id: UUID) -> bool:
        raise NotImplementedError

    def feature_set_belongs_to_project(self, project_id: UUID, feature_set_id: UUID) -> bool:
        raise NotImplementedError

    def get_drift_signal(self, drift_report_id: UUID) -> DriftRetrainingSignal | None:
        raise NotImplementedError

    def get_alert_signal(self, alert_event_id: UUID) -> AlertRetrainingSignal | None:
        raise NotImplementedError


class TrainingRunLauncher(Protocol):
    def launch_training_run(
        self,
        request: RetrainingTrainingRequest,
        principal: Principal,
    ) -> RetrainingTrainingLaunch:
        raise NotImplementedError
