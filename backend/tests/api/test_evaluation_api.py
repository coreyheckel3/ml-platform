from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from forgeml.main import create_app
from forgeml.modules.evaluation.api.routes import get_evaluation_comparison_service
from forgeml.modules.evaluation.domain.entities import (
    EvaluationApprovalChecklistItem,
    EvaluationComparisonSummary,
    EvaluationLeaderboardEntry,
    EvaluationMetricSlice,
    EvaluationModelCard,
    EvaluationModelMetric,
)
from forgeml.platform.api.dependencies import get_current_principal
from forgeml.platform.security.rbac import Principal


@dataclass
class FakeEvaluationComparisonService:
    project_id: object

    def get_evaluation_comparison_summary(self, query, principal):
        assert query.project_id == self.project_id
        now = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
        experiment_run_id = uuid4()
        model_version_id = uuid4()
        return EvaluationComparisonSummary(
            schema_version="forgeml.evaluation_comparison.v1",
            project_id=self.project_id,
            project_name="Fraud Detection",
            project_slug="fraud-detection",
            project_status="active",
            primary_metric_name="auc",
            higher_is_better=True,
            candidate_count=1,
            recommended_experiment_run_id=experiment_run_id,
            leaderboard=(
                EvaluationLeaderboardEntry(
                    rank=1,
                    experiment_run_id=experiment_run_id,
                    run_name="xgb-depth-8",
                    experiment_name="Fraud Risk Baseline",
                    status="succeeded",
                    model_type="binary_classifier",
                    primary_metric_name="auc",
                    primary_metric_value=0.96,
                    delta_from_baseline=0.0,
                    quality_score=100,
                    model_version_label="Fraud Risk XGB v2",
                    approval_status="approved",
                    evidence_summary="Fraud Risk XGB v2 is approved with registry evidence.",
                ),
            ),
            metric_slices=(
                EvaluationMetricSlice(
                    metric_name="auc",
                    candidate_count=1,
                    best_value=0.96,
                    baseline_value=0.96,
                    delta_from_baseline=0.0,
                    best_experiment_run_id=experiment_run_id,
                    best_run_name="xgb-depth-8",
                    higher_is_better=True,
                ),
            ),
            model_cards=(
                EvaluationModelCard(
                    model_version_id=model_version_id,
                    model_name="Fraud Risk XGB",
                    version=2,
                    status="approved",
                    approval_status="approved",
                    model_format="xgboost-booster",
                    metric_summary=(
                        EvaluationModelMetric(label="auc", value=0.96, tone="success"),
                    ),
                    signature_summary=("1 inputs", "1 outputs"),
                    artifact_uri="s3://forgeml/models/fraud-risk-xgb/v2",
                    artifact_manifest_uri="s3://forgeml/models/fraud-risk-xgb/v2/manifest.json",
                    artifact_manifest_hash="sha256:model-manifest",
                    lineage_summary=("dataset_version:validated",),
                    risk_flags=(),
                ),
            ),
            approval_checklist=(
                EvaluationApprovalChecklistItem(
                    key="offline_metrics",
                    label="Offline metrics",
                    status="passed",
                    detail="1 metrics are attached to the candidate run.",
                    evidence="xgb-depth-8",
                ),
            ),
            narrative=("xgb-depth-8 currently leads the comparison on auc=0.9600.",),
            generated_at=now,
        )


def test_evaluation_route_exposes_project_comparison_summary() -> None:
    organization_id = uuid4()
    user_id = uuid4()
    project_id = uuid4()
    service = FakeEvaluationComparisonService(project_id=project_id)
    app = create_app()
    app.dependency_overrides[get_evaluation_comparison_service] = lambda: service
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        user_id=str(user_id),
        email="owner@example.com",
        organization_id=str(organization_id),
        permissions=frozenset({"*"}),
    )
    client = TestClient(app)

    response = client.get(f"/api/v1/projects/{project_id}/evaluation/comparison")

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "forgeml.evaluation_comparison.v1"
    assert payload["project_name"] == "Fraud Detection"
    assert payload["primary_metric_name"] == "auc"
    assert payload["leaderboard"][0]["run_name"] == "xgb-depth-8"
    assert payload["metric_slices"][0]["best_value"] == 0.96
    assert payload["model_cards"][0]["model_name"] == "Fraud Risk XGB"
    assert payload["approval_checklist"][0]["status"] == "passed"
    assert payload["generated_at"] == "2026-01-15T12:00:00+00:00"
