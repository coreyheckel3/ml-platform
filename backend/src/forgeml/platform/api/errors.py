from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from forgeml.platform.api.problem_details import (
    http_problem_details,
    internal_problem_details,
    problem_details_response,
    validation_problem_details,
)
from forgeml.platform.domain.errors import ForgeMLError


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ForgeMLError)
    async def handle_forgeml_error(request: Request, exc: ForgeMLError) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", None)
        return JSONResponse(
            status_code=exc.status_code,
            content=problem_details_response(
                code=exc.code,
                status_code=exc.status_code,
                detail=exc.message,
                trace_id=trace_id,
                errors=exc.details,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", None)
        return JSONResponse(
            status_code=422,
            content=validation_problem_details(trace_id=trace_id, errors=exc.errors()),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", None)
        return JSONResponse(
            status_code=exc.status_code,
            content=http_problem_details(
                status_code=exc.status_code,
                detail=exc.detail,
                trace_id=trace_id,
            ),
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, _exc: Exception) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", None)
        return JSONResponse(
            status_code=500,
            content=internal_problem_details(trace_id=trace_id),
        )
