from pydantic import BaseModel, Field


class EvaluationLeaderboardEntryResponse(BaseModel):
    rank: int
    experiment_run_id: str
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


class EvaluationMetricSliceResponse(BaseModel):
    metric_name: str
    candidate_count: int
    best_value: float
    baseline_value: float
    delta_from_baseline: float
    best_experiment_run_id: str
    best_run_name: str
    higher_is_better: bool


class EvaluationModelMetricResponse(BaseModel):
    label: str
    value: float
    tone: str


class EvaluationModelCardResponse(BaseModel):
    model_version_id: str
    model_name: str
    version: int
    status: str
    approval_status: str
    model_format: str
    metric_summary: list[EvaluationModelMetricResponse] = Field(default_factory=list)
    signature_summary: list[str] = Field(default_factory=list)
    artifact_uri: str
    artifact_manifest_uri: str
    artifact_manifest_hash: str
    lineage_summary: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)


class EvaluationApprovalChecklistItemResponse(BaseModel):
    key: str
    label: str
    status: str
    detail: str
    evidence: str


class EvaluationComparisonSummaryResponse(BaseModel):
    schema_version: str = "forgeml.evaluation_comparison.v1"
    project_id: str
    project_name: str
    project_slug: str
    project_status: str
    primary_metric_name: str | None
    higher_is_better: bool
    candidate_count: int
    recommended_experiment_run_id: str | None
    leaderboard: list[EvaluationLeaderboardEntryResponse] = Field(default_factory=list)
    metric_slices: list[EvaluationMetricSliceResponse] = Field(default_factory=list)
    model_cards: list[EvaluationModelCardResponse] = Field(default_factory=list)
    approval_checklist: list[EvaluationApprovalChecklistItemResponse] = Field(
        default_factory=list
    )
    narrative: list[str] = Field(default_factory=list)
    generated_at: str
