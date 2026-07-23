from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    features: dict[str, Any] = Field(default_factory=dict)


class PredictionResponse(BaseModel):
    prediction: dict[str, Any]
    model_version_id: str
    deployment_revision_id: str
    latency_ms: float


def create_app() -> FastAPI:
    app = FastAPI(title="ForgeML Inference Runtime", version="0.1.0")

    @app.get("/health/live")
    def live() -> dict[str, str]:
        return {"status": "live"}

    @app.get("/health/ready")
    def ready() -> dict[str, str]:
        return {"status": "ready"}

    @app.post("/predict", response_model=PredictionResponse)
    def predict(request: PredictionRequest) -> PredictionResponse:
        return PredictionResponse(
            prediction={"score": 0.0, "features_seen": len(request.features)},
            model_version_id="local-development",
            deployment_revision_id="local-development",
            latency_ms=0.0,
        )

    return app


def main() -> None:
    import os

    import uvicorn

    uvicorn.run(
        create_app(),
        host=os.getenv("FORGEML_RUNTIME_HOST", "127.0.0.1"),
        port=8080,
    )


if __name__ == "__main__":
    main()
