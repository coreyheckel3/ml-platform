from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from forgeml.modules.evaluation.application.services import (
    EvaluationComparisonService,
    GetEvaluationComparisonQuery,
)
from forgeml.modules.evaluation.domain.entities import (
    EvaluationCandidate,
    EvaluationComparisonSnapshot,
    EvaluationModelEvidence,
)
from forgeml.platform.domain.errors import PermissionDeniedError, ResourceNotFoundError
from forgeml.platform.security.rbac import Principal


class FakeEvaluationRepository:
    def __init__(self, snapshot: EvaluationComparisonSnapshot | None) -> None:
        self.snapshot = snapshot
        self.received_organization_id: UUID | None = None
        self.received_project_id: UUID | None = None

    def load_snapshot(
        self,
        organization_id: UUID,
        project_id: UUID,
    ) -> EvaluationComparisonSnapshot | None:
        self.received_organization_id = organization_id
        self.received_project_id = project_id
        return self.snapshot


def test_evaluation_service_builds_ranked_model_comparison() -> None:
    organization_id = uuid4()
    project_id = uuid4()
    champion_run_id = uuid4()
    baseline_run_id = uuid4()
    repository = FakeEvaluationRepository(
        _snapshot(project_id, champion_run_id, baseline_run_id)
    )
    service = EvaluationComparisonService(repository=repository)

    summary = service.get_evaluation_comparison_summary(
        GetEvaluationComparisonQuery(
            organization_id=organization_id,
            project_id=project_id,
        ),
        _principal(organization_id),
    )

    assert summary.schema_version == "forgeml.evaluation_comparison.v1"
    assert summary.project_name == "Fraud Detection"
    assert summary.primary_metric_name == "auc"
    assert summary.higher_is_better is True
    assert summary.candidate_count == 2
    assert summary.recommended_experiment_run_id == champion_run_id
    assert summary.leaderboard[0].experiment_run_id == champion_run_id
    assert summary.leaderboard[0].rank == 1
    assert summary.leaderboard[0].primary_metric_value == 0.96
    assert summary.leaderboard[0].delta_from_baseline == pytest.approx(0.04)
    assert summary.leaderboard[0].approval_status == "approved"
    assert summary.metric_slices[0].metric_name == "auc"
    assert summary.metric_slices[0].best_run_name == "xgb-depth-8"
    assert summary.metric_slices[1].metric_name == "log_loss"
    assert summary.metric_slices[1].higher_is_better is False
    assert summary.metric_slices[1].delta_from_baseline == pytest.approx(0.05)
    assert summary.model_cards[0].model_name == "Fraud Risk XGB"
    assert summary.model_cards[0].metric_summary[0].label == "auc"
    assert summary.model_cards[0].risk_flags == ()
    assert all(item.status == "passed" for item in summary.approval_checklist)
    assert "xgb-depth-8 currently leads" in summary.narrative[0]
    assert repository.received_organization_id == organization_id
    assert repository.received_project_id == project_id


def test_evaluation_service_handles_missing_candidates() -> None:
    organization_id = uuid4()
    project_id = uuid4()
    service = EvaluationComparisonService(
        repository=FakeEvaluationRepository(
            EvaluationComparisonSnapshot(
                project_id=project_id,
                project_name="Semantic Search",
                project_slug="semantic-search",
                project_status="active",
                candidates=(),
                model_evidence=(),
            )
        )
    )

    summary = service.get_evaluation_comparison_summary(
        GetEvaluationComparisonQuery(
            organization_id=organization_id,
            project_id=project_id,
        ),
        _principal(organization_id),
    )

    assert summary.primary_metric_name is None
    assert summary.recommended_experiment_run_id is None
    assert summary.leaderboard == ()
    assert summary.metric_slices == ()
    assert summary.approval_checklist[0].status == "missing"
    assert "No evaluation candidates" in summary.narrative[0]


def test_evaluation_service_rejects_missing_permission() -> None:
    organization_id = uuid4()
    service = EvaluationComparisonService(repository=FakeEvaluationRepository(None))

    with pytest.raises(PermissionDeniedError):
        service.get_evaluation_comparison_summary(
            GetEvaluationComparisonQuery(
                organization_id=organization_id,
                project_id=uuid4(),
            ),
            Principal(
                user_id=str(uuid4()),
                email="viewer@example.com",
                organization_id=str(organization_id),
                permissions=frozenset({"projects:read"}),
            ),
        )


def test_evaluation_service_rejects_cross_organization_query() -> None:
    service = EvaluationComparisonService(repository=FakeEvaluationRepository(None))

    with pytest.raises(PermissionDeniedError):
        service.get_evaluation_comparison_summary(
            GetEvaluationComparisonQuery(
                organization_id=uuid4(),
                project_id=uuid4(),
            ),
            _principal(uuid4()),
        )


def test_evaluation_service_raises_not_found_for_missing_project() -> None:
    organization_id = uuid4()
    service = EvaluationComparisonService(repository=FakeEvaluationRepository(None))

    with pytest.raises(ResourceNotFoundError):
        service.get_evaluation_comparison_summary(
            GetEvaluationComparisonQuery(
                organization_id=organization_id,
                project_id=uuid4(),
            ),
            _principal(organization_id),
        )


def _principal(organization_id: UUID) -> Principal:
    return Principal(
        user_id=str(uuid4()),
        email="owner@example.com",
        organization_id=str(organization_id),
        permissions=frozenset({"evaluation:read"}),
    )


def _snapshot(
    project_id: UUID,
    champion_run_id: UUID,
    baseline_run_id: UUID,
) -> EvaluationComparisonSnapshot:
    now = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
    experiment_id = uuid4()
    champion_training_id = uuid4()
    model_version_id = uuid4()
    return EvaluationComparisonSnapshot(
        project_id=project_id,
        project_name="Fraud Detection",
        project_slug="fraud-detection",
        project_status="active",
        candidates=(
            EvaluationCandidate(
                experiment_id=experiment_id,
                experiment_name="Fraud Risk Baseline",
                experiment_run_id=baseline_run_id,
                run_name="xgb-depth-4",
                status="succeeded",
                model_type="binary_classifier",
                training_run_id=uuid4(),
                model_version_id=None,
                registered_model_name=None,
                model_version=None,
                model_version_status=None,
                approval_status="not_registered",
                objective_metric_name="auc",
                metrics={"auc": 0.92, "log_loss": 0.23},
                parameters={"max_depth": 4},
                evaluation_report={"slice_metrics": {"high_value": {"auc": 0.9}}},
                dataset_version_id=uuid4(),
                feature_set_id=uuid4(),
                artifact_uri="s3://forgeml/training-runs/baseline",
                artifact_manifest_uri="",
                artifact_manifest_hash="",
                created_at=now,
                updated_at=now,
            ),
            EvaluationCandidate(
                experiment_id=experiment_id,
                experiment_name="Fraud Risk Baseline",
                experiment_run_id=champion_run_id,
                run_name="xgb-depth-8",
                status="succeeded",
                model_type="binary_classifier",
                training_run_id=champion_training_id,
                model_version_id=model_version_id,
                registered_model_name="Fraud Risk XGB",
                model_version=2,
                model_version_status="approved",
                approval_status="approved",
                objective_metric_name="auc",
                metrics={"auc": 0.96, "log_loss": 0.18},
                parameters={"max_depth": 8},
                evaluation_report={"slice_metrics": {"high_value": {"auc": 0.95}}},
                dataset_version_id=uuid4(),
                feature_set_id=uuid4(),
                artifact_uri="s3://forgeml/models/fraud-risk-xgb/v2",
                artifact_manifest_uri="s3://forgeml/models/fraud-risk-xgb/v2/manifest.json",
                artifact_manifest_hash="sha256:manifest",
                created_at=now,
                updated_at=now,
            ),
        ),
        model_evidence=(
            EvaluationModelEvidence(
                registered_model_id=uuid4(),
                registered_model_name="Fraud Risk XGB",
                model_version_id=model_version_id,
                version=2,
                status="approved",
                approval_status="approved",
                model_format="xgboost-booster",
                signature={
                    "inputs": [{"name": "amount"}],
                    "outputs": [{"name": "risk_score"}],
                },
                metrics={"auc": 0.96, "log_loss": 0.18},
                artifact_uri="s3://forgeml/models/fraud-risk-xgb/v2",
                artifact_manifest_uri="s3://forgeml/models/fraud-risk-xgb/v2/manifest.json",
                artifact_manifest_hash="sha256:manifest",
                lineage_sources=("dataset_version:validated", "feature_set:merchant"),
                training_run_id=champion_training_id,
                experiment_run_id=champion_run_id,
            ),
        ),
    )
