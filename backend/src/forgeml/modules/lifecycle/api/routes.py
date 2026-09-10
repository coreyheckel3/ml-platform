from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from forgeml.modules.lifecycle.api.schemas import (
    ProjectLifecycleDependencyResponse,
    ProjectLifecycleMetricResponse,
    ProjectLifecycleStageResponse,
    ProjectLifecycleSummaryResponse,
)
from forgeml.modules.lifecycle.application.services import (
    GetProjectLifecycleSummaryQuery,
    ProjectLifecycleService,
)
from forgeml.modules.lifecycle.domain.entities import (
    ProjectLifecycleDependency,
    ProjectLifecycleMetric,
    ProjectLifecycleStage,
    ProjectLifecycleSummary,
)
from forgeml.modules.lifecycle.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyProjectLifecycleRepository,
)
from forgeml.platform.api.dependencies import get_current_principal, get_db_session
from forgeml.platform.security.rbac import Principal

router = APIRouter(tags=["lifecycle"])


def get_project_lifecycle_service(
    session: Session = Depends(get_db_session),
) -> ProjectLifecycleService:
    return ProjectLifecycleService(
        repository=SqlAlchemyProjectLifecycleRepository(session),
    )


@router.get(
    "/projects/{project_id}/lifecycle/summary",
    response_model=ProjectLifecycleSummaryResponse,
)
def get_project_lifecycle_summary(
    project_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: ProjectLifecycleService = Depends(get_project_lifecycle_service),
) -> ProjectLifecycleSummaryResponse:
    return _summary_response(
        service.get_project_lifecycle_summary(
            GetProjectLifecycleSummaryQuery(
                organization_id=UUID(principal.organization_id),
                project_id=project_id,
            ),
            principal,
        )
    )


def _summary_response(
    summary: ProjectLifecycleSummary,
) -> ProjectLifecycleSummaryResponse:
    return ProjectLifecycleSummaryResponse(
        schema_version=summary.schema_version,
        project_id=str(summary.project_id),
        project_name=summary.project_name,
        project_slug=summary.project_slug,
        project_status=summary.project_status,
        readiness_score=summary.readiness_score,
        ready_stage_count=summary.ready_stage_count,
        total_stage_count=summary.total_stage_count,
        stages=[_stage_response(stage) for stage in summary.stages],
        dependencies=[
            _dependency_response(dependency) for dependency in summary.dependencies
        ],
        metrics=[_metric_response(metric) for metric in summary.metrics],
        recommended_actions=list(summary.recommended_actions),
        generated_at=summary.generated_at.isoformat(),
    )


def _stage_response(stage: ProjectLifecycleStage) -> ProjectLifecycleStageResponse:
    return ProjectLifecycleStageResponse(
        key=stage.key,
        title=stage.title,
        status=stage.status,
        description=stage.description,
        primary_signal=stage.primary_signal,
        count=stage.count,
        last_updated_at=(
            stage.last_updated_at.isoformat() if stage.last_updated_at else None
        ),
        route_path=stage.route_path,
        recommended_action=stage.recommended_action,
    )


def _dependency_response(
    dependency: ProjectLifecycleDependency,
) -> ProjectLifecycleDependencyResponse:
    return ProjectLifecycleDependencyResponse(
        source_stage=dependency.source_stage,
        target_stage=dependency.target_stage,
        status=dependency.status,
        detail=dependency.detail,
    )


def _metric_response(metric: ProjectLifecycleMetric) -> ProjectLifecycleMetricResponse:
    return ProjectLifecycleMetricResponse(
        label=metric.label,
        value=metric.value,
        detail=metric.detail,
        tone=metric.tone,
    )
