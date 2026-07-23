from fastapi import APIRouter
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
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


@metrics_router.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
