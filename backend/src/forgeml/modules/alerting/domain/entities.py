from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class AlertSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertMetric(StrEnum):
    INFERENCE_ERROR_RATE = "inference_error_rate"
    INFERENCE_P95_LATENCY_MS = "inference_p95_latency_ms"
    INFERENCE_PREDICTION_COUNT = "inference_prediction_count"


class AlertOperator(StrEnum):
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"


class AlertEventStatus(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


@dataclass(frozen=True)
class AlertRule:
    id: UUID
    organization_id: UUID
    project_id: UUID
    name: str
    slug: str
    description: str
    severity: AlertSeverity
    metric: AlertMetric
    operator: AlertOperator
    threshold: float
    window_seconds: int
    enabled: bool
    created_by: UUID


@dataclass(frozen=True)
class AlertEvent:
    id: UUID
    organization_id: UUID
    project_id: UUID
    alert_rule_id: UUID
    endpoint_id: UUID | None
    severity: AlertSeverity
    status: AlertEventStatus
    message: str
    observed_value: float
    threshold: float
    metadata: dict[str, object]
    acknowledged_by: UUID | None
    resolved_by: UUID | None


@dataclass(frozen=True)
class EndpointMetricSnapshotReference:
    endpoint_id: UUID
    organization_id: UUID
    project_id: UUID
    endpoint_name: str
    route_path: str
    window_seconds: int
    prediction_count: int
    error_count: int
    p50_latency_ms: float
    p95_latency_ms: float


@dataclass(frozen=True)
class AlertEvaluation:
    rule_id: UUID
    endpoint_id: UUID
    triggered: bool
    observed_value: float
    event: AlertEvent | None
