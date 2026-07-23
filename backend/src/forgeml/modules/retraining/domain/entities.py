from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class RetrainingPolicyStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class RetrainingTriggerType(StrEnum):
    DRIFT = "drift"
    ALERT = "alert"
    MANUAL = "manual"


class RetrainingRunStatus(StrEnum):
    SKIPPED = "skipped"
    PENDING_APPROVAL = "pending_approval"
    QUEUED = "queued"
    FAILED = "failed"
    REJECTED = "rejected"


class RetrainingDecision(StrEnum):
    TRIGGERED = "triggered"
    SKIPPED = "skipped"
    PENDING_APPROVAL = "pending_approval"


@dataclass(frozen=True)
class RetrainingPolicy:
    id: UUID
    organization_id: UUID
    project_id: UUID
    deployment_id: UUID
    name: str
    slug: str
    description: str
    trigger_type: RetrainingTriggerType
    trigger_config: dict[str, object]
    training_template: dict[str, object]
    cooldown_seconds: int
    max_runs_per_day: int
    approval_required: bool
    enabled: bool
    status: RetrainingPolicyStatus
    created_by: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class RetrainingRun:
    id: UUID
    organization_id: UUID
    project_id: UUID
    policy_id: UUID
    deployment_id: UUID
    trigger_type: RetrainingTriggerType
    drift_report_id: UUID | None
    alert_event_id: UUID | None
    training_run_id: UUID | None
    status: RetrainingRunStatus
    reason: str
    training_config: dict[str, object]
    decision_metadata: dict[str, object]
    requested_by: UUID
    approved_by: UUID | None
    rejected_by: UUID | None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class DriftRetrainingSignal:
    drift_report_id: UUID
    organization_id: UUID
    project_id: UUID
    deployment_id: UUID
    endpoint_id: UUID
    drift_score: float
    drifted_feature_count: int
    evaluated_feature_count: int
    status: str
    created_at: datetime | None = None


@dataclass(frozen=True)
class AlertRetrainingSignal:
    alert_event_id: UUID
    organization_id: UUID
    project_id: UUID
    endpoint_id: UUID | None
    deployment_id: UUID | None
    severity: str
    status: str
    observed_value: float
    threshold: float
    metadata: dict[str, object]
    created_at: datetime | None = None


@dataclass(frozen=True)
class RetrainingTrainingRequest:
    organization_id: UUID
    project_id: UUID
    experiment_id: UUID
    run_name: str
    dataset_version_id: UUID | None
    feature_set_id: UUID | None
    algorithm: str
    model_type: str
    objective_metric_name: str
    hyperparameters: dict[str, object]
    requested_by: UUID


@dataclass(frozen=True)
class RetrainingTrainingLaunch:
    training_run_id: UUID
    status: str
    orchestrator_run_id: str


@dataclass(frozen=True)
class RetrainingEvaluation:
    policy_id: UUID
    decision: RetrainingDecision
    triggered: bool
    reason: str
    run: RetrainingRun | None
