from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from forgeml import __version__
from forgeml.modules.alerting.api.routes import router as alerting_router
from forgeml.modules.auth.api.routes import router as auth_router
from forgeml.modules.datasets.api.routes import router as datasets_router
from forgeml.modules.deployments.api.routes import router as deployments_router
from forgeml.modules.drift_detection.api.routes import router as drift_detection_router
from forgeml.modules.experiments.api.routes import router as experiments_router
from forgeml.modules.feature_store.api.routes import router as feature_store_router
from forgeml.modules.inference.api.routes import router as inference_router
from forgeml.modules.model_registry.api.routes import router as model_registry_router
from forgeml.modules.monitoring.api.routes import router as monitoring_router
from forgeml.modules.projects.api.routes import router as projects_router
from forgeml.modules.retraining.api.routes import router as retraining_router
from forgeml.modules.training.api.routes import router as training_router
from forgeml.platform.api.errors import install_error_handlers
from forgeml.platform.api.middleware import (
    RateLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from forgeml.platform.config import Settings, get_settings
from forgeml.platform.database.session import configure_database
from forgeml.platform.observability.metrics import metrics_router


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_database(resolved_settings)

    app = FastAPI(
        title="ForgeML",
        version=__version__,
        docs_url="/docs" if resolved_settings.enable_docs else None,
        redoc_url="/redoc" if resolved_settings.enable_docs else None,
    )
    app.state.settings = resolved_settings

    app.add_middleware(
        RateLimitMiddleware,
        enabled=resolved_settings.rate_limit_enabled,
        requests_per_window=resolved_settings.rate_limit_requests,
        window_seconds=resolved_settings.rate_limit_window_seconds,
        exempt_paths=resolved_settings.rate_limit_exempt_paths,
    )
    app.add_middleware(SecurityHeadersMiddleware, environment=resolved_settings.environment)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    install_error_handlers(app)

    @app.get("/health/live", tags=["health"])
    def live() -> dict[str, str]:
        return {"status": "live", "service": resolved_settings.service_name}

    @app.get("/health/ready", tags=["health"])
    def ready() -> dict[str, str]:
        return {"status": "ready", "service": resolved_settings.service_name}

    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(projects_router, prefix="/api/v1")
    app.include_router(datasets_router, prefix="/api/v1")
    app.include_router(feature_store_router, prefix="/api/v1")
    app.include_router(experiments_router, prefix="/api/v1")
    app.include_router(training_router, prefix="/api/v1")
    app.include_router(model_registry_router, prefix="/api/v1")
    app.include_router(deployments_router, prefix="/api/v1")
    app.include_router(inference_router, prefix="/api/v1")
    app.include_router(monitoring_router, prefix="/api/v1")
    app.include_router(alerting_router, prefix="/api/v1")
    app.include_router(drift_detection_router, prefix="/api/v1")
    app.include_router(retraining_router, prefix="/api/v1")
    app.include_router(metrics_router)
    return app


app = create_app()
