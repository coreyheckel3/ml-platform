from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from forgeml.modules.lifecycle.application.services import (
    GetProjectLifecycleSummaryQuery,
    ProjectLifecycleService,
)
from forgeml.modules.lifecycle.domain.entities import ProjectLifecycleSnapshot
from forgeml.platform.domain.errors import PermissionDeniedError, ResourceNotFoundError
from forgeml.platform.security.rbac import Principal


class FakeLifecycleRepository:
    def __init__(self, snapshot: ProjectLifecycleSnapshot | None) -> None:
        self.snapshot = snapshot
        self.received_organization_id: UUID | None = None
        self.received_project_id: UUID | None = None

    def load_snapshot(
        self,
        organization_id: UUID,
        project_id: UUID,
    ) -> ProjectLifecycleSnapshot | None:
        self.received_organization_id = organization_id
        self.received_project_id = project_id
        return self.snapshot


def test_lifecycle_service_builds_ready_project_summary() -> None:
    organization_id = uuid4()
    project_id = uuid4()
    repository = FakeLifecycleRepository(_snapshot(project_id))
    service = ProjectLifecycleService(repository=repository)

    summary = service.get_project_lifecycle_summary(
        GetProjectLifecycleSummaryQuery(
            organization_id=organization_id,
            project_id=project_id,
        ),
        _principal(organization_id),
    )

    assert summary.schema_version == "forgeml.project_lifecycle.v1"
    assert summary.project_name == "Fraud Detection"
    assert summary.readiness_score == 100
    assert summary.ready_stage_count == summary.total_stage_count == 10
    assert [stage.key for stage in summary.stages] == [
        "datasets",
        "feature_store",
        "experiments",
        "training",
        "model_registry",
        "deployment",
        "inference",
        "monitoring",
        "drift_detection",
        "retraining",
    ]
    assert all(stage.status == "ready" for stage in summary.stages)
    assert summary.dependencies[0].status == "connected"
    assert summary.metrics[0].label == "Dataset Versions"
    assert summary.recommended_actions == ()
    assert repository.received_organization_id == organization_id
    assert repository.received_project_id == project_id


def test_lifecycle_service_surfaces_missing_and_attention_states() -> None:
    organization_id = uuid4()
    project_id = uuid4()
    service = ProjectLifecycleService(
        repository=FakeLifecycleRepository(
            _snapshot(
                project_id,
                validation_runs=0,
                materializations=0,
                succeeded_training_runs=0,
                approved_model_versions=0,
                active_deployments=0,
                prediction_count=0,
                alert_rules=0,
                drift_reports=0,
                successful_retraining_runs=0,
            )
        )
    )

    summary = service.get_project_lifecycle_summary(
        GetProjectLifecycleSummaryQuery(
            organization_id=organization_id,
            project_id=project_id,
        ),
        _principal(organization_id),
    )

    stages_by_key = {stage.key: stage for stage in summary.stages}
    assert stages_by_key["datasets"].status == "needs_attention"
    assert stages_by_key["feature_store"].status == "needs_attention"
    assert stages_by_key["training"].status == "needs_attention"
    assert stages_by_key["monitoring"].status == "missing"
    assert stages_by_key["drift_detection"].status == "needs_attention"
    assert summary.readiness_score < 100
    assert "Register a dataset version" in summary.recommended_actions[0]


def test_lifecycle_service_rejects_missing_permission() -> None:
    organization_id = uuid4()
    project_id = uuid4()
    service = ProjectLifecycleService(
        repository=FakeLifecycleRepository(_snapshot(project_id))
    )

    with pytest.raises(PermissionDeniedError):
        service.get_project_lifecycle_summary(
            GetProjectLifecycleSummaryQuery(
                organization_id=organization_id,
                project_id=project_id,
            ),
            Principal(
                user_id=str(uuid4()),
                email="viewer@example.com",
                organization_id=str(organization_id),
                permissions=frozenset({"projects:read"}),
            ),
        )


def test_lifecycle_service_rejects_cross_organization_query() -> None:
    service = ProjectLifecycleService(repository=FakeLifecycleRepository(None))

    with pytest.raises(PermissionDeniedError):
        service.get_project_lifecycle_summary(
            GetProjectLifecycleSummaryQuery(
                organization_id=uuid4(),
                project_id=uuid4(),
            ),
            _principal(uuid4()),
        )


def test_lifecycle_service_raises_not_found_for_missing_project() -> None:
    organization_id = uuid4()
    service = ProjectLifecycleService(repository=FakeLifecycleRepository(None))

    with pytest.raises(ResourceNotFoundError):
        service.get_project_lifecycle_summary(
            GetProjectLifecycleSummaryQuery(
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
        permissions=frozenset({"lifecycle:read"}),
    )


def _snapshot(project_id: UUID, **overrides: object) -> ProjectLifecycleSnapshot:
    values = {
        "project_id": project_id,
        "project_name": "Fraud Detection",
        "project_slug": "fraud-detection",
        "project_status": "active",
        "datasets": 1,
        "dataset_versions": 2,
        "validation_runs": 2,
        "feature_sets": 1,
        "feature_pipelines": 1,
        "materializations": 1,
        "experiments": 1,
        "experiment_runs": 3,
        "training_runs": 3,
        "succeeded_training_runs": 2,
        "failed_training_runs": 1,
        "registered_models": 1,
        "model_versions": 2,
        "approved_model_versions": 1,
        "deployments": 1,
        "active_deployments": 1,
        "inference_endpoints": 1,
        "active_inference_endpoints": 1,
        "prediction_count": 1200,
        "request_count": 1200,
        "inference_error_count": 4,
        "max_p95_latency_ms": 48.2,
        "drift_profiles": 1,
        "drift_reports": 2,
        "breached_drift_reports": 1,
        "alert_rules": 2,
        "active_alert_events": 1,
        "retraining_policies": 1,
        "enabled_retraining_policies": 1,
        "retraining_runs": 2,
        "successful_retraining_runs": 1,
        "queued_retraining_runs": 1,
        "last_updated_at": datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
    }
    values.update(overrides)
    return ProjectLifecycleSnapshot(**values)
