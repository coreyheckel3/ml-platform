from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from forgeml.main import create_app
from forgeml.platform.domain.errors import DomainValidationError


class ErrorProbePayload(BaseModel):
    name: str


def test_domain_error_response_uses_problem_details_shape() -> None:
    app = create_app()

    @app.get("/test-errors/domain")
    def domain_error() -> None:
        raise DomainValidationError(
            "Project name is invalid.",
            details=[{"loc": ["body", "name"], "msg": "Unsupported value"}],
        )

    client = TestClient(app)

    response = client.get("/test-errors/domain", headers={"x-request-id": "trace-domain"})
    payload = response.json()

    assert response.status_code == 422
    assert response.headers["x-request-id"] == "trace-domain"
    assert payload == {
        "type": "https://forgeml.dev/errors/validation_failed",
        "title": "Validation Failed",
        "status": 422,
        "detail": "Project name is invalid.",
        "trace_id": "trace-domain",
        "errors": [{"loc": ["body", "name"], "msg": "Unsupported value"}],
    }


def test_request_validation_response_uses_problem_details_shape() -> None:
    app = create_app()

    @app.post("/test-errors/validation")
    def validation_error(_payload: ErrorProbePayload) -> dict[str, bool]:
        return {"ok": True}

    client = TestClient(app)

    response = client.post(
        "/test-errors/validation",
        json={"password": "unsafe-secret"},
        headers={"x-request-id": "trace-validation"},
    )
    payload = response.json()

    assert response.status_code == 422
    assert payload["type"] == "https://forgeml.dev/errors/validation_failed"
    assert payload["title"] == "Validation Failed"
    assert payload["detail"] == "Request validation failed."
    assert payload["trace_id"] == "trace-validation"
    assert payload["errors"][0]["loc"] == ["body", "name"]
    assert payload["errors"][0]["type"] == "missing"
    assert "unsafe-secret" not in response.text


def test_http_exception_response_uses_problem_details_shape() -> None:
    app = create_app()

    @app.get("/test-errors/http")
    def http_error() -> None:
        raise HTTPException(status_code=404, detail="Project was not found.")

    client = TestClient(app)

    response = client.get("/test-errors/http", headers={"x-request-id": "trace-http"})
    payload = response.json()

    assert response.status_code == 404
    assert payload["type"] == "https://forgeml.dev/errors/resource_not_found"
    assert payload["title"] == "Resource Not Found"
    assert payload["detail"] == "Project was not found."
    assert payload["trace_id"] == "trace-http"
    assert payload["errors"] == []


def test_unhandled_exception_response_is_sanitized() -> None:
    app = create_app()

    @app.get("/test-errors/internal")
    def internal_error() -> None:
        raise RuntimeError("database password leaked")

    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/test-errors/internal", headers={"x-request-id": "trace-internal"})
    payload = response.json()

    assert response.status_code == 500
    assert payload == {
        "type": "https://forgeml.dev/errors/internal_error",
        "title": "Internal Error",
        "status": 500,
        "detail": "An unexpected error occurred.",
        "trace_id": "trace-internal",
        "errors": [],
    }
    assert "password" not in response.text
