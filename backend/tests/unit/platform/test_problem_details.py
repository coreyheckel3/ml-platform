from forgeml.platform.api.problem_details import (
    INTERNAL_ERROR_DETAIL,
    PROBLEM_TYPE_BASE_URL,
    http_problem_details,
    internal_problem_details,
    normalize_validation_errors,
    problem_details_response,
    validation_problem_details,
)


def test_problem_details_response_has_stable_shape() -> None:
    response = problem_details_response(
        code="conflict",
        status_code=409,
        detail="Project already exists.",
        trace_id="trace-123",
        errors=[{"field": "name"}],
    )

    assert response == {
        "type": f"{PROBLEM_TYPE_BASE_URL}/conflict",
        "title": "Conflict",
        "status": 409,
        "detail": "Project already exists.",
        "trace_id": "trace-123",
        "errors": [{"field": "name"}],
    }


def test_validation_problem_details_omits_raw_input_values() -> None:
    response = validation_problem_details(
        trace_id="trace-123",
        errors=[
            {
                "loc": ("body", "password"),
                "msg": "Field required",
                "type": "missing",
                "input": "unsafe-secret",
            }
        ],
    )

    assert response["status"] == 422
    assert response["detail"] == "Request validation failed."
    assert response["errors"] == [
        {"loc": ["body", "password"], "msg": "Field required", "type": "missing"}
    ]
    assert "unsafe-secret" not in str(response)


def test_http_problem_details_maps_common_status_codes() -> None:
    response = http_problem_details(status_code=404, detail="Not Found", trace_id="trace-123")

    assert response["type"] == f"{PROBLEM_TYPE_BASE_URL}/resource_not_found"
    assert response["title"] == "Resource Not Found"
    assert response["status"] == 404
    assert response["detail"] == "Not Found"


def test_internal_problem_details_uses_sanitized_message() -> None:
    response = internal_problem_details(trace_id="trace-123")

    assert response["type"] == f"{PROBLEM_TYPE_BASE_URL}/internal_error"
    assert response["detail"] == INTERNAL_ERROR_DETAIL
    assert response["errors"] == []


def test_normalize_validation_errors_handles_non_sequence_location() -> None:
    errors = normalize_validation_errors(
        [{"loc": "query", "msg": "Invalid value", "type": "value_error"}]
    )

    assert errors == [{"loc": ["query"], "msg": "Invalid value", "type": "value_error"}]
