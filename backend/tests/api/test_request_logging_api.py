import logging

from fastapi.testclient import TestClient

from forgeml.main import create_app
from forgeml.platform.config import Settings
from forgeml.platform.observability.logging import REDACTED_VALUE, REQUEST_LOGGER_NAME


def test_request_logging_emits_structured_event(caplog) -> None:
    caplog.set_level(logging.INFO, logger=REQUEST_LOGGER_NAME)
    client = TestClient(create_app())

    response = client.get(
        "/health/live?project=fraud&access_token=unsafe",
        headers={"x-request-id": "trace-123"},
    )

    assert response.status_code == 200
    events = [
        record.event
        for record in caplog.records
        if record.name == REQUEST_LOGGER_NAME and hasattr(record, "event")
    ]
    assert events
    event = events[-1]
    assert event["schema_version"] == "forgeml.request_log.v1"
    assert event["trace_id"] == "trace-123"
    assert event["service"] == "forgeml-api"
    assert event["environment"] == "local"
    assert event["http"]["method"] == "GET"
    assert event["http"]["route"] == "/health/live"
    assert event["http"]["status_code"] == 200
    assert event["http"]["status_class"] == "2xx"
    assert event["http"]["query_params"]["project"] == "fraud"
    assert event["http"]["query_params"]["access_token"] == REDACTED_VALUE
    assert "unsafe" not in str(event)


def test_request_logging_can_be_disabled(caplog) -> None:
    caplog.set_level(logging.INFO, logger=REQUEST_LOGGER_NAME)
    settings = Settings(request_logging_enabled=False)
    client = TestClient(create_app(settings))

    response = client.get("/health/live", headers={"x-request-id": "trace-disabled"})

    assert response.status_code == 200
    assert [
        record
        for record in caplog.records
        if record.name == REQUEST_LOGGER_NAME and getattr(record, "event", {}).get("trace_id")
        == "trace-disabled"
    ] == []
