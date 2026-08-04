from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from typing import Any

REQUEST_LOG_SCHEMA_VERSION = "forgeml.request_log.v1"
REQUEST_LOGGER_NAME = "forgeml.http"
REDACTED_VALUE = "[redacted]"
SENSITIVE_FIELD_MARKERS = frozenset(
    {
        "authorization",
        "cookie",
        "passwd",
        "password",
        "secret",
        "token",
        "api_key",
        "api-key",
        "x-api-key",
    }
)
REQUEST_LOG_REQUIRED_TOP_LEVEL_FIELDS = (
    "schema_version",
    "event_name",
    "service",
    "environment",
    "trace_id",
    "http",
)
REQUEST_LOG_REQUIRED_HTTP_FIELDS = (
    "method",
    "route",
    "path",
    "status_code",
    "status_class",
    "duration_ms",
    "client_host",
    "query_params",
)


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC)
            .isoformat()
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        event = getattr(record, "event", None)
        if isinstance(event, Mapping):
            payload["event"] = _json_safe(event)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def configure_structured_logging(*, enabled: bool, level: str) -> None:
    if not enabled:
        return

    root_logger = logging.getLogger()
    root_logger.setLevel(_level_number(level))
    formatter = JsonLogFormatter()
    if not root_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
        return

    for handler in root_logger.handlers:
        handler.setFormatter(formatter)


def build_http_request_log_event(
    *,
    service: str,
    environment: str,
    trace_id: str,
    method: str,
    route: str,
    path: str,
    status_code: int,
    duration_seconds: float,
    client_host: str,
    query_params: Iterable[tuple[str, Any]] | Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": REQUEST_LOG_SCHEMA_VERSION,
        "event_name": "http.request",
        "service": service,
        "environment": environment,
        "trace_id": trace_id,
        "http": {
            "method": method.upper(),
            "route": route,
            "path": path,
            "status_code": status_code,
            "status_class": f"{status_code // 100}xx",
            "duration_ms": round(duration_seconds * 1000, 3),
            "client_host": client_host,
            "query_params": redact_mapping(query_params),
        },
    }


def redact_mapping(
    values: Iterable[tuple[str, Any]] | Mapping[str, Any],
) -> dict[str, Any]:
    items = values.items() if isinstance(values, Mapping) else values
    redacted: dict[str, Any] = {}
    for key, value in items:
        normalized_key = str(key)
        if _is_sensitive_field(normalized_key):
            redacted[normalized_key] = REDACTED_VALUE
            continue
        redacted[normalized_key] = _normalize_log_value(value)
    return redacted


def log_http_request(event: Mapping[str, Any]) -> None:
    logging.getLogger(REQUEST_LOGGER_NAME).info("http_request", extra={"event": dict(event)})


def _level_number(level: str) -> int:
    resolved = logging.getLevelName(level.upper())
    if isinstance(resolved, int):
        return resolved
    return logging.INFO


def _is_sensitive_field(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(marker.replace("-", "_") in normalized for marker in SENSITIVE_FIELD_MARKERS)


def _normalize_log_value(value: Any) -> Any:
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    if isinstance(value, tuple | list):
        return [_normalize_log_value(item) for item in value]
    return str(value)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_json_safe(item) for item in value]
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)
