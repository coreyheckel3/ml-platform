import json
import logging

from forgeml.platform.observability.logging import (
    REDACTED_VALUE,
    REQUEST_LOG_SCHEMA_VERSION,
    JsonLogFormatter,
    build_http_request_log_event,
    redact_mapping,
)


def test_redact_mapping_scrubs_sensitive_fields() -> None:
    redacted = redact_mapping(
        {
            "project": "fraud",
            "access_token": "token-value",
            "Authorization": "Bearer token-value",
            "password": "unsafe",
        }
    )

    assert redacted["project"] == "fraud"
    assert redacted["access_token"] == REDACTED_VALUE
    assert redacted["Authorization"] == REDACTED_VALUE
    assert redacted["password"] == REDACTED_VALUE


def test_build_http_request_log_event_has_stable_shape() -> None:
    event = build_http_request_log_event(
        service="forgeml-api",
        environment="staging",
        trace_id="trace-123",
        method="get",
        route="/api/v1/projects",
        path="/api/v1/projects",
        status_code=201,
        duration_seconds=0.01567,
        client_host="203.0.113.10",
        query_params=[("project", "fraud"), ("refresh_token", "unsafe")],
    )

    assert event["schema_version"] == REQUEST_LOG_SCHEMA_VERSION
    assert event["event_name"] == "http.request"
    assert event["service"] == "forgeml-api"
    assert event["environment"] == "staging"
    assert event["trace_id"] == "trace-123"
    assert event["http"] == {
        "method": "GET",
        "route": "/api/v1/projects",
        "path": "/api/v1/projects",
        "status_code": 201,
        "status_class": "2xx",
        "duration_ms": 15.67,
        "client_host": "203.0.113.10",
        "query_params": {
            "project": "fraud",
            "refresh_token": REDACTED_VALUE,
        },
    }


def test_json_log_formatter_serializes_event_payload() -> None:
    record = logging.LogRecord(
        name="forgeml.http",
        level=logging.INFO,
        pathname=__file__,
        lineno=42,
        msg="http_request",
        args=(),
        exc_info=None,
    )
    record.event = {"schema_version": REQUEST_LOG_SCHEMA_VERSION, "trace_id": "trace-123"}

    payload = json.loads(JsonLogFormatter().format(record))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "forgeml.http"
    assert payload["message"] == "http_request"
    assert payload["event"]["schema_version"] == REQUEST_LOG_SCHEMA_VERSION
    assert payload["event"]["trace_id"] == "trace-123"
    assert payload["timestamp"].endswith("Z")
