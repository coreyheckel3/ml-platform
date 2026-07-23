from pydantic import BaseModel, Field


class CreateRetrainingPolicyRequest(BaseModel):
    deployment_id: str
    name: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=2000)
    trigger_type: str = Field(pattern="^(drift|alert|manual)$")
    trigger_config: dict[str, object] = Field(default_factory=dict)
    training_template: dict[str, object] = Field(default_factory=dict)
    cooldown_seconds: int = Field(default=3600, ge=0, le=604800)
    max_runs_per_day: int = Field(default=3, ge=1, le=50)
    approval_required: bool = True
    enabled: bool = True


class EvaluateRetrainingPolicyRequest(BaseModel):
    drift_report_id: str | None = None
    alert_event_id: str | None = None
    reason: str = Field(default="", max_length=2000)


class TriggerRetrainingRunRequest(BaseModel):
    reason: str = Field(default="", max_length=2000)


class RetrainingPolicyResponse(BaseModel):
    id: str
    organization_id: str
    project_id: str
    deployment_id: str
    name: str
    slug: str
    description: str
    trigger_type: str
    trigger_config: dict[str, object]
    training_template: dict[str, object]
    cooldown_seconds: int
    max_runs_per_day: int
    approval_required: bool
    enabled: bool
    status: str
    created_by: str
    created_at: str | None
    updated_at: str | None


class RetrainingPolicyListResponse(BaseModel):
    items: list[RetrainingPolicyResponse]
    next_cursor: str | None = None


class RetrainingRunResponse(BaseModel):
    id: str
    organization_id: str
    project_id: str
    policy_id: str
    deployment_id: str
    trigger_type: str
    drift_report_id: str | None
    alert_event_id: str | None
    training_run_id: str | None
    status: str
    reason: str
    training_config: dict[str, object]
    decision_metadata: dict[str, object]
    requested_by: str
    approved_by: str | None
    rejected_by: str | None
    created_at: str | None
    updated_at: str | None


class RetrainingRunListResponse(BaseModel):
    items: list[RetrainingRunResponse]
    next_cursor: str | None = None


class RetrainingEvaluationResponse(BaseModel):
    policy_id: str
    decision: str
    triggered: bool
    reason: str
    run: RetrainingRunResponse | None
