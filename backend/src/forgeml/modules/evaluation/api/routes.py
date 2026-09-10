from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from forgeml.modules.evaluation.api.schemas import (
    EvaluationApprovalChecklistItemResponse,
    EvaluationComparisonSummaryResponse,
    EvaluationLeaderboardEntryResponse,
    EvaluationMetricSliceResponse,
    EvaluationModelCardResponse,
    EvaluationModelMetricResponse,
)
from forgeml.modules.evaluation.application.services import (
    EvaluationComparisonService,
    GetEvaluationComparisonQuery,
)
from forgeml.modules.evaluation.domain.entities import (
    EvaluationApprovalChecklistItem,
    EvaluationComparisonSummary,
    EvaluationLeaderboardEntry,
    EvaluationMetricSlice,
    EvaluationModelCard,
    EvaluationModelMetric,
)
from forgeml.modules.evaluation.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyEvaluationComparisonRepository,
)
from forgeml.platform.api.dependencies import get_current_principal, get_db_session
from forgeml.platform.security.rbac import Principal

router = APIRouter(tags=["evaluation"])


def get_evaluation_comparison_service(
    session: Session = Depends(get_db_session),
) -> EvaluationComparisonService:
    return EvaluationComparisonService(
        repository=SqlAlchemyEvaluationComparisonRepository(session),
    )


@router.get(
    "/projects/{project_id}/evaluation/comparison",
    response_model=EvaluationComparisonSummaryResponse,
)
def get_evaluation_comparison_summary(
    project_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: EvaluationComparisonService = Depends(get_evaluation_comparison_service),
) -> EvaluationComparisonSummaryResponse:
    return _summary_response(
        service.get_evaluation_comparison_summary(
            GetEvaluationComparisonQuery(
                organization_id=UUID(principal.organization_id),
                project_id=project_id,
            ),
            principal,
        )
    )


def _summary_response(
    summary: EvaluationComparisonSummary,
) -> EvaluationComparisonSummaryResponse:
    return EvaluationComparisonSummaryResponse(
        schema_version=summary.schema_version,
        project_id=str(summary.project_id),
        project_name=summary.project_name,
        project_slug=summary.project_slug,
        project_status=summary.project_status,
        primary_metric_name=summary.primary_metric_name,
        higher_is_better=summary.higher_is_better,
        candidate_count=summary.candidate_count,
        recommended_experiment_run_id=(
            str(summary.recommended_experiment_run_id)
            if summary.recommended_experiment_run_id
            else None
        ),
        leaderboard=[_leaderboard_response(entry) for entry in summary.leaderboard],
        metric_slices=[_metric_slice_response(metric) for metric in summary.metric_slices],
        model_cards=[_model_card_response(model_card) for model_card in summary.model_cards],
        approval_checklist=[
            _approval_checklist_response(item) for item in summary.approval_checklist
        ],
        narrative=list(summary.narrative),
        generated_at=summary.generated_at.isoformat(),
    )


def _leaderboard_response(
    entry: EvaluationLeaderboardEntry,
) -> EvaluationLeaderboardEntryResponse:
    return EvaluationLeaderboardEntryResponse(
        rank=entry.rank,
        experiment_run_id=str(entry.experiment_run_id),
        run_name=entry.run_name,
        experiment_name=entry.experiment_name,
        status=entry.status,
        model_type=entry.model_type,
        primary_metric_name=entry.primary_metric_name,
        primary_metric_value=entry.primary_metric_value,
        delta_from_baseline=entry.delta_from_baseline,
        quality_score=entry.quality_score,
        model_version_label=entry.model_version_label,
        approval_status=entry.approval_status,
        evidence_summary=entry.evidence_summary,
    )


def _metric_slice_response(
    metric: EvaluationMetricSlice,
) -> EvaluationMetricSliceResponse:
    return EvaluationMetricSliceResponse(
        metric_name=metric.metric_name,
        candidate_count=metric.candidate_count,
        best_value=metric.best_value,
        baseline_value=metric.baseline_value,
        delta_from_baseline=metric.delta_from_baseline,
        best_experiment_run_id=str(metric.best_experiment_run_id),
        best_run_name=metric.best_run_name,
        higher_is_better=metric.higher_is_better,
    )


def _model_card_response(model_card: EvaluationModelCard) -> EvaluationModelCardResponse:
    return EvaluationModelCardResponse(
        model_version_id=str(model_card.model_version_id),
        model_name=model_card.model_name,
        version=model_card.version,
        status=model_card.status,
        approval_status=model_card.approval_status,
        model_format=model_card.model_format,
        metric_summary=[_model_metric_response(metric) for metric in model_card.metric_summary],
        signature_summary=list(model_card.signature_summary),
        artifact_uri=model_card.artifact_uri,
        artifact_manifest_uri=model_card.artifact_manifest_uri,
        artifact_manifest_hash=model_card.artifact_manifest_hash,
        lineage_summary=list(model_card.lineage_summary),
        risk_flags=list(model_card.risk_flags),
    )


def _model_metric_response(metric: EvaluationModelMetric) -> EvaluationModelMetricResponse:
    return EvaluationModelMetricResponse(
        label=metric.label,
        value=metric.value,
        tone=metric.tone,
    )


def _approval_checklist_response(
    item: EvaluationApprovalChecklistItem,
) -> EvaluationApprovalChecklistItemResponse:
    return EvaluationApprovalChecklistItemResponse(
        key=item.key,
        label=item.label,
        status=item.status,
        detail=item.detail,
        evidence=item.evidence,
    )
