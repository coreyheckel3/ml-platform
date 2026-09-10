from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

EVALUATION_COMPARISON_SCHEMA_VERSION = "forgeml.evaluation_comparison.v1"


@dataclass(frozen=True)
class EvaluationCandidate:
    experiment_id: UUID
    experiment_name: str
    experiment_run_id: UUID
    run_name: str
    status: str
    model_type: str
    training_run_id: UUID | None
    model_version_id: UUID | None
    registered_model_name: str | None
    model_version: int | None
    model_version_status: str | None
    approval_status: str
    objective_metric_name: str | None
    metrics: dict[str, float]
    parameters: dict[str, object]
    evaluation_report: dict[str, object]
    dataset_version_id: UUID | None
    feature_set_id: UUID | None
    artifact_uri: str
    artifact_manifest_uri: str
    artifact_manifest_hash: str
    created_at: datetime | None
    updated_at: datetime | None


@dataclass(frozen=True)
class EvaluationModelEvidence:
    registered_model_id: UUID
    registered_model_name: str
    model_version_id: UUID
    version: int
    status: str
    approval_status: str
    model_format: str
    signature: dict[str, object]
    metrics: dict[str, float]
    artifact_uri: str
    artifact_manifest_uri: str
    artifact_manifest_hash: str
    lineage_sources: tuple[str, ...]
    training_run_id: UUID
    experiment_run_id: UUID


@dataclass(frozen=True)
class EvaluationComparisonSnapshot:
    project_id: UUID
    project_name: str
    project_slug: str
    project_status: str
    candidates: tuple[EvaluationCandidate, ...]
    model_evidence: tuple[EvaluationModelEvidence, ...]


@dataclass(frozen=True)
class EvaluationLeaderboardEntry:
    rank: int
    experiment_run_id: UUID
    run_name: str
    experiment_name: str
    status: str
    model_type: str
    primary_metric_name: str | None
    primary_metric_value: float | None
    delta_from_baseline: float | None
    quality_score: int
    model_version_label: str | None
    approval_status: str
    evidence_summary: str


@dataclass(frozen=True)
class EvaluationMetricSlice:
    metric_name: str
    candidate_count: int
    best_value: float
    baseline_value: float
    delta_from_baseline: float
    best_experiment_run_id: UUID
    best_run_name: str
    higher_is_better: bool


@dataclass(frozen=True)
class EvaluationModelMetric:
    label: str
    value: float
    tone: str


@dataclass(frozen=True)
class EvaluationModelCard:
    model_version_id: UUID
    model_name: str
    version: int
    status: str
    approval_status: str
    model_format: str
    metric_summary: tuple[EvaluationModelMetric, ...]
    signature_summary: tuple[str, ...]
    artifact_uri: str
    artifact_manifest_uri: str
    artifact_manifest_hash: str
    lineage_summary: tuple[str, ...]
    risk_flags: tuple[str, ...]


@dataclass(frozen=True)
class EvaluationApprovalChecklistItem:
    key: str
    label: str
    status: str
    detail: str
    evidence: str


@dataclass(frozen=True)
class EvaluationComparisonSummary:
    schema_version: str
    project_id: UUID
    project_name: str
    project_slug: str
    project_status: str
    primary_metric_name: str | None
    higher_is_better: bool
    candidate_count: int
    recommended_experiment_run_id: UUID | None
    leaderboard: tuple[EvaluationLeaderboardEntry, ...]
    metric_slices: tuple[EvaluationMetricSlice, ...]
    model_cards: tuple[EvaluationModelCard, ...]
    approval_checklist: tuple[EvaluationApprovalChecklistItem, ...]
    narrative: tuple[str, ...]
    generated_at: datetime
