from pydantic import BaseModel, Field


class CreateAlertRuleRequest(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=2000)
    severity: str = Field(pattern="^(info|warning|critical)$")
    metric: str = Field(
        pattern="^(inference_error_rate|inference_p95_latency_ms|inference_prediction_count)$"
    )
    operator: str = Field(pattern="^(gt|gte|lt|lte)$")
    threshold: float = Field(ge=0)
    window_seconds: int = Field(gt=0, le=86_400)
    enabled: bool = True


class AlertRuleResponse(BaseModel):
    id: str
    organization_id: str
    project_id: str
    name: str
    slug: str
    description: str
    severity: str
    metric: str
    operator: str
    threshold: float
    window_seconds: int
    enabled: bool
    created_by: str


class AlertRuleListResponse(BaseModel):
    items: list[AlertRuleResponse]
    next_cursor: str | None = None


class EvaluateAlertRuleRequest(BaseModel):
    endpoint_id: str


class AlertEventResponse(BaseModel):
    id: str
    organization_id: str
    project_id: str
    alert_rule_id: str
    endpoint_id: str | None
    severity: str
    status: str
    message: str
    observed_value: float
    threshold: float
    metadata: dict[str, object]
    acknowledged_by: str | None
    resolved_by: str | None


class AlertEventListResponse(BaseModel):
    items: list[AlertEventResponse]
    next_cursor: str | None = None


class AlertEvaluationResponse(BaseModel):
    rule_id: str
    endpoint_id: str
    triggered: bool
    observed_value: float
    event: AlertEventResponse | None
