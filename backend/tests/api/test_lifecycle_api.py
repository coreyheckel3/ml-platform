from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from forgeml.main import create_app
from forgeml.modules.lifecycle.api.routes import get_project_lifecycle_service
from forgeml.modules.lifecycle.domain.entities import (
    ProjectLifecycleDependency,
    ProjectLifecycleMetric,
    ProjectLifecycleStage,
    ProjectLifecycleSummary,
)
from forgeml.platform.api.dependencies import get_current_principal
from forgeml.platform.security.rbac import Principal


@dataclass
class FakeProjectLifecycleService:
    project_id: object

    def get_project_lifecycle_summary(self, query, principal):
        assert query.project_id == self.project_id
        now = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
        return ProjectLifecycleSummary(
            schema_version="forgeml.project_lifecycle.v1",
            project_id=self.project_id,
            project_name="Fraud Detection",
            project_slug="fraud-detection",
            project_status="active",
            readiness_score=80,
            ready_stage_count=8,
            total_stage_count=10,
            stages=(
                ProjectLifecycleStage(
                    key="datasets",
                    title="Datasets",
                    status="ready",
                    description="Registered datasets.",
                    primary_signal="2 versions, 2 validation runs",
                    count=2,
                    last_updated_at=now,
                    route_path="/datasets",
                    recommended_action="Keep dataset contracts current.",
                ),
            ),
            dependencies=(
                ProjectLifecycleDependency(
                    source_stage="datasets",
                    target_stage="feature_store",
                    status="connected",
                    detail="Datasets feeds Feature Store.",
                ),
            ),
            metrics=(
                ProjectLifecycleMetric(
                    label="Predictions",
                    value="1200",
                    detail="0.33% error rate",
                    tone="success",
                ),
            ),
            recommended_actions=("Approve one model version.",),
            generated_at=now,
        )


def test_lifecycle_route_exposes_project_summary() -> None:
    organization_id = uuid4()
    user_id = uuid4()
    project_id = uuid4()
    service = FakeProjectLifecycleService(project_id=project_id)
    app = create_app()
    app.dependency_overrides[get_project_lifecycle_service] = lambda: service
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        user_id=str(user_id),
        email="owner@example.com",
        organization_id=str(organization_id),
        permissions=frozenset({"*"}),
    )
    client = TestClient(app)

    response = client.get(f"/api/v1/projects/{project_id}/lifecycle/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "forgeml.project_lifecycle.v1"
    assert payload["project_name"] == "Fraud Detection"
    assert payload["readiness_score"] == 80
    assert payload["stages"][0]["key"] == "datasets"
    assert payload["stages"][0]["last_updated_at"] == "2026-01-15T12:00:00+00:00"
    assert payload["dependencies"][0]["status"] == "connected"
    assert payload["metrics"][0]["label"] == "Predictions"
    assert payload["recommended_actions"] == ["Approve one model version."]
