from __future__ import annotations

from http import HTTPStatus
from typing import Any

from pydantic import BaseModel, Field

PROBLEM_DETAILS_SCHEMA_VERSION = "forgeml.problem_details.v1"
PROBLEM_TYPE_BASE_URL = "https://forgeml.dev/errors"
INTERNAL_ERROR_DETAIL = "An unexpected error occurred."
VALIDATION_ERROR_DETAIL = "Request validation failed."
PROBLEM_DETAILS_REQUIRED_FIELDS = (
    "type",
    "title",
    "status",
    "detail",
    "trace_id",
    "errors",
)
VALIDATION_ERROR_REQUIRED_FIELDS = ("loc", "msg", "type")


class ProblemDetails(BaseModel):
    type: str
    title: str
    status: int = Field(ge=400, le=599)
    detail: str
    trace_id: str | None
    errors: list[dict[str, Any]] = Field(default_factory=list)


def problem_details_response(
    *,
    code: str,
    status_code: int,
    detail: str,
    trace_id: str | None,
    errors: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return ProblemDetails(
        type=f"{PROBLEM_TYPE_BASE_URL}/{code}",
        title=_title_for_code(code),
        status=status_code,
        detail=detail,
        trace_id=trace_id,
        errors=errors or [],
    ).model_dump()


def validation_problem_details(
    *,
    trace_id: str | None,
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    return problem_details_response(
        code="validation_failed",
        status_code=422,
        detail=VALIDATION_ERROR_DETAIL,
        trace_id=trace_id,
        errors=normalize_validation_errors(errors),
    )


def http_problem_details(
    *,
    status_code: int,
    detail: Any,
    trace_id: str | None,
) -> dict[str, Any]:
    return problem_details_response(
        code=_http_error_code(status_code),
        status_code=status_code,
        detail=_safe_http_detail(status_code, detail),
        trace_id=trace_id,
    )


def internal_problem_details(*, trace_id: str | None) -> dict[str, Any]:
    return problem_details_response(
        code="internal_error",
        status_code=500,
        detail=INTERNAL_ERROR_DETAIL,
        trace_id=trace_id,
    )


def normalize_validation_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized_errors: list[dict[str, Any]] = []
    for error in errors:
        loc = error.get("loc", ())
        if isinstance(loc, tuple | list):
            location = [str(item) for item in loc]
        else:
            location = [str(loc)]
        normalized_errors.append(
            {
                "loc": location,
                "msg": str(error.get("msg", "Invalid value.")),
                "type": str(error.get("type", "value_error")),
            }
        )
    return normalized_errors


def _http_error_code(status_code: int) -> str:
    if status_code == 401:
        return "authentication_failed"
    if status_code == 403:
        return "permission_denied"
    if status_code == 404:
        return "resource_not_found"
    if status_code == 409:
        return "conflict"
    if status_code == 422:
        return "validation_failed"
    return f"http_{status_code}"


def _safe_http_detail(status_code: int, detail: Any) -> str:
    if isinstance(detail, str) and detail:
        return detail
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "HTTP error"


def _title_for_code(code: str) -> str:
    return code.replace("_", " ").title()
