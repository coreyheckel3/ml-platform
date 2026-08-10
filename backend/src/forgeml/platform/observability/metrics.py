from fastapi import APIRouter
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.responses import Response

metrics_router = APIRouter(tags=["observability"])

api_requests_total = Counter(
    "forgeml_api_requests_total",
    "Total API requests.",
    ["route", "method", "status_code"],
)
api_request_duration_seconds = Histogram(
    "forgeml_api_request_duration_seconds",
    "API request duration.",
    ["route", "method"],
)
rate_limited_requests_total = Counter(
    "forgeml_rate_limited_requests_total",
    "Total API requests rejected by rate limiting.",
    ["route", "method"],
)
model_promotions_total = Counter(
    "forgeml_model_promotions_total",
    "Total model version promotions from training runs.",
    ["status"],
)
training_worker_claims_total = Counter(
    "forgeml_training_worker_claims_total",
    "Total training run claim attempts by outcome.",
    ["outcome"],
)
training_worker_heartbeats_total = Counter(
    "forgeml_training_worker_heartbeats_total",
    "Total training worker heartbeat attempts by outcome.",
    ["outcome"],
)
training_worker_retries_total = Counter(
    "forgeml_training_worker_retries_total",
    "Total training worker retry decisions by outcome.",
    ["outcome"],
)
training_worker_expired_leases_total = Counter(
    "forgeml_training_worker_expired_leases_total",
    "Total expired training run leases recovered by outcome.",
    ["outcome"],
)
mlflow_tracking_sync_total = Counter(
    "forgeml_mlflow_tracking_sync_total",
    "Total MLflow tracking sync attempts by outcome.",
    ["outcome"],
)
readiness_probe_status = Gauge(
    "forgeml_readiness_probe_status",
    "Readiness probe status, where 1 is pass and 0 is fail.",
    ["probe"],
)
readiness_probe_duration_seconds = Histogram(
    "forgeml_readiness_probe_duration_seconds",
    "Readiness probe duration.",
    ["probe"],
)


@metrics_router.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
