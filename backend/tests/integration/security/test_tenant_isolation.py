from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from forgeml.modules.administration.infrastructure.sqlalchemy_models import AuditLogModel
from forgeml.modules.administration.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyAuditLogRepository,
)
from forgeml.modules.administration.repositories.interfaces import AuditLogFilters
from forgeml.modules.auth.infrastructure.sqlalchemy_models import UserModel
from forgeml.modules.datasets.domain.entities import DatasetSourceType, DatasetStatus
from forgeml.modules.datasets.infrastructure.sqlalchemy_models import (
    DatasetModel,
    DatasetVersionModel,
)
from forgeml.modules.datasets.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyDatasetRepository,
)
from forgeml.modules.experiments.infrastructure.sqlalchemy_models import (
    ExperimentModel,
    ExperimentRunModel,
)
from forgeml.modules.feature_store.infrastructure.sqlalchemy_models import FeatureSetModel
from forgeml.modules.projects.infrastructure.sqlalchemy_models import (
    OrganizationModel,
    ProjectModel,
)
from forgeml.modules.projects.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyProjectRepository,
)
from forgeml.modules.training.domain.entities import TrainingRunStatus
from forgeml.modules.training.infrastructure.sqlalchemy_models import TrainingRunModel
from forgeml.modules.training.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyTrainingRunRepository,
)
from forgeml.platform.database.base import Base

_SQLALCHEMY_MODEL_DEPENDENCIES = (
    DatasetVersionModel,
    ExperimentModel,
    ExperimentRunModel,
    FeatureSetModel,
)


def test_repository_queries_do_not_cross_tenant_boundaries() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    tenant_a = _TenantSeed(
        organization_id=uuid4(),
        user_id=uuid4(),
        project_id=uuid4(),
        dataset_id=uuid4(),
        training_run_id=uuid4(),
    )
    tenant_b = _TenantSeed(
        organization_id=uuid4(),
        user_id=uuid4(),
        project_id=uuid4(),
        dataset_id=uuid4(),
        training_run_id=uuid4(),
    )

    with Session(engine) as session:
        _seed_tenant(session, tenant_a, slug_suffix="a")
        _seed_tenant(session, tenant_b, slug_suffix="b")
        session.commit()

    with Session(engine) as session:
        projects = SqlAlchemyProjectRepository(session)
        datasets = SqlAlchemyDatasetRepository(session)
        training_runs = SqlAlchemyTrainingRunRepository(session)
        audit_log = SqlAlchemyAuditLogRepository(session)

        visible_projects = projects.list_for_organization(tenant_a.organization_id)
        visible_datasets = datasets.list_datasets(
            tenant_a.organization_id,
            tenant_a.project_id,
        )
        visible_training_runs = training_runs.list_training_runs(
            tenant_a.organization_id,
            tenant_a.project_id,
        )
        runnable_training_runs = training_runs.list_runnable_training_runs(
            tenant_a.organization_id,
            None,
            limit=10,
            now=datetime.now(tz=UTC),
        )
        expired_training_runs = training_runs.list_expired_running_training_runs(
            tenant_a.organization_id,
            None,
            limit=10,
            now=datetime.now(tz=UTC),
        )
        visible_audit_entries = audit_log.list_entries(
            tenant_a.organization_id,
            filters=AuditLogFilters(),
            limit=20,
        )

    assert {project.id for project in visible_projects} == {tenant_a.project_id}
    assert {dataset.id for dataset in visible_datasets} == {tenant_a.dataset_id}
    assert {run.id for run in visible_training_runs} == {tenant_a.training_run_id}
    assert {run.id for run in runnable_training_runs} == {tenant_a.training_run_id}
    assert {run.id for run in expired_training_runs} == set()
    assert {entry.organization_id for entry in visible_audit_entries} == {
        tenant_a.organization_id
    }
    assert tenant_b.project_id not in {project.id for project in visible_projects}
    assert tenant_b.dataset_id not in {dataset.id for dataset in visible_datasets}
    assert tenant_b.training_run_id not in {run.id for run in visible_training_runs}


class _TenantSeed:
    def __init__(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        project_id: UUID,
        dataset_id: UUID,
        training_run_id: UUID,
    ) -> None:
        self.organization_id = organization_id
        self.user_id = user_id
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.training_run_id = training_run_id


def _seed_tenant(session: Session, tenant: _TenantSeed, *, slug_suffix: str) -> None:
    session.add(
        OrganizationModel(
            id=tenant.organization_id,
            name=f"Tenant {slug_suffix.upper()}",
            slug=f"tenant-{slug_suffix}",
        )
    )
    session.add(
        UserModel(
            id=tenant.user_id,
            organization_id=tenant.organization_id,
            email=f"owner-{slug_suffix}@example.com",
            display_name="Owner",
            password_hash="hash",
            permissions_csv="*",
        )
    )
    session.add(
        ProjectModel(
            id=tenant.project_id,
            organization_id=tenant.organization_id,
            name=f"Fraud {slug_suffix.upper()}",
            slug="fraud",
            owner_user_id=tenant.user_id,
        )
    )
    session.add(
        DatasetModel(
            id=tenant.dataset_id,
            organization_id=tenant.organization_id,
            project_id=tenant.project_id,
            name=f"Transactions {slug_suffix.upper()}",
            slug="transactions",
            description="",
            source_type=DatasetSourceType.UPLOAD.value,
            status=DatasetStatus.ACTIVE.value,
        )
    )
    session.add(
        TrainingRunModel(
            id=tenant.training_run_id,
            organization_id=tenant.organization_id,
            project_id=tenant.project_id,
            experiment_id=uuid4(),
            experiment_run_id=uuid4(),
            dataset_version_id=None,
            feature_set_id=None,
            algorithm="xgboost",
            model_type="binary_classifier",
            objective_metric_name="auc",
            hyperparameters_json={"max_depth": 4},
            status=TrainingRunStatus.QUEUED.value,
            requested_by=tenant.user_id,
            artifact_uri=f"s3://forgeml/{tenant.training_run_id}",
            orchestrator_run_id=f"workflow-{slug_suffix}",
            metrics_json={},
            error_message=None,
            attempt_count=0,
            max_attempts=3,
            worker_id=None,
            lease_expires_at=datetime.now(tz=UTC) + timedelta(minutes=5),
            last_heartbeat_at=None,
            queued_at=datetime.now(tz=UTC),
            started_at=None,
            completed_at=None,
            next_retry_at=None,
        )
    )
    session.add(
        AuditLogModel(
            id=uuid4(),
            organization_id=tenant.organization_id,
            actor_type="user",
            actor_id=str(tenant.user_id),
            action="projects.create",
            resource_type="project",
            resource_id=str(tenant.project_id),
            metadata_json={"slug": "fraud"},
        )
    )
