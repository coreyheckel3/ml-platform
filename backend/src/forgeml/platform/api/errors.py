from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from forgeml.platform.domain.errors import ForgeMLError


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ForgeMLError)
    async def handle_forgeml_error(request: Request, exc: ForgeMLError) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", None)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "type": f"https://forgeml.dev/errors/{exc.code}",
                "title": exc.code.replace("_", " ").title(),
                "status": exc.status_code,
                "detail": exc.message,
                "trace_id": trace_id,
                "errors": exc.details,
            },
        )

