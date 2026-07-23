from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from forgeml.modules.model_registry.domain.entities import (
    ModelApproval,
    ModelApprovalStatus,
    ModelLineage,
    ModelVersion,
    ModelVersionStatus,
    RegisteredModel,
    RegisteredModelStatus,
    TrainingRunReference,
)
from forgeml.modules.model_registry.infrastructure.sqlalchemy_models import (
    ModelApprovalModel,
    ModelLineageModel,
    ModelVersionModel,
    RegisteredModelModel,
)
from forgeml.modules.training.infrastructure.sqlalchemy_models import TrainingRunModel


class SqlAlchemyModelRegistryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_registered_model(self, model: RegisteredModel) -> RegisteredModel:
        record = RegisteredModelModel(
            id=model.id,
            organization_id=model.organization_id,
            project_id=model.project_id,
            name=model.name,
            slug=model.slug,
            description=model.description,
            task_type=model.task_type,
            owner_user_id=model.owner_user_id,
            status=model.status.value,
        )
        self._session.add(record)
        self._session.flush()
        return _registered_model_to_domain(record)

    def get_registered_model(self, model_id: UUID) -> RegisteredModel | None:
        record = self._session.get(RegisteredModelModel, model_id)
        return _registered_model_to_domain(record) if record else None

    def list_registered_models(
        self,
        organization_id: UUID,
        project_id: UUID,
    ) -> list[RegisteredModel]:
        records = self._session.scalars(
            select(RegisteredModelModel)
            .where(
                RegisteredModelModel.organization_id == organization_id,
                RegisteredModelModel.project_id == project_id,
            )
            .order_by(RegisteredModelModel.name)
        ).all()
        return [_registered_model_to_domain(record) for record in records]

    def registered_model_slug_exists(
        self,
        organization_id: UUID,
        project_id: UUID,
        slug: str,
    ) -> bool:
        return (
            self._session.scalar(
                select(RegisteredModelModel.id).where(
                    RegisteredModelModel.organization_id == organization_id,
                    RegisteredModelModel.project_id == project_id,
                    RegisteredModelModel.slug == slug,
                )
            )
            is not None
        )

    def get_training_run_reference(self, training_run_id: UUID) -> TrainingRunReference | None:
        record = self._session.get(TrainingRunModel, training_run_id)
        if record is None:
            return None
        return TrainingRunReference(
            id=record.id,
            organization_id=record.organization_id,
            project_id=record.project_id,
            experiment_id=record.experiment_id,
            experiment_run_id=record.experiment_run_id,
            dataset_version_id=record.dataset_version_id,
            feature_set_id=record.feature_set_id,
            status=record.status,
            artifact_uri=record.artifact_uri,
            model_type=record.model_type,
            metrics={key: float(value) for key, value in record.metrics_json.items()},
        )

    def training_run_already_registered(
        self,
        registered_model_id: UUID,
        training_run_id: UUID,
    ) -> bool:
        return (
            self._session.scalar(
                select(ModelVersionModel.id).where(
                    ModelVersionModel.registered_model_id == registered_model_id,
                    ModelVersionModel.training_run_id == training_run_id,
                )
            )
            is not None
        )

    def latest_model_version_number(self, registered_model_id: UUID) -> int:
        versions = self._session.scalars(
            select(ModelVersionModel.version).where(
                ModelVersionModel.registered_model_id == registered_model_id
            )
        ).all()
        return max(versions, default=0)

    def add_model_version(self, version: ModelVersion) -> ModelVersion:
        record = ModelVersionModel(
            id=version.id,
            registered_model_id=version.registered_model_id,
            version=version.version,
            training_run_id=version.training_run_id,
            experiment_run_id=version.experiment_run_id,
            artifact_uri=version.artifact_uri,
            model_format=version.model_format,
            signature_json=version.signature,
            metrics_json=version.metrics,
            status=version.status.value,
            created_by=version.created_by,
        )
        self._session.add(record)
        self._session.flush()
        return _model_version_to_domain(record)

    def get_model_version(self, version_id: UUID) -> ModelVersion | None:
        record = self._session.get(ModelVersionModel, version_id)
        return _model_version_to_domain(record) if record else None

    def list_model_versions(self, registered_model_id: UUID) -> list[ModelVersion]:
        records = self._session.scalars(
            select(ModelVersionModel)
            .where(ModelVersionModel.registered_model_id == registered_model_id)
            .order_by(ModelVersionModel.version.desc())
        ).all()
        return [_model_version_to_domain(record) for record in records]

    def update_model_version(self, version: ModelVersion) -> ModelVersion:
        record = self._session.get(ModelVersionModel, version.id)
        if record is None:
            raise ValueError("Model version does not exist.")
        record.status = version.status.value
        record.metrics_json = version.metrics
        record.signature_json = version.signature
        self._session.flush()
        return _model_version_to_domain(record)

    def add_approval(self, approval: ModelApproval) -> ModelApproval:
        record = ModelApprovalModel(
            id=approval.id,
            model_version_id=approval.model_version_id,
            status=approval.status.value,
            requested_by=approval.requested_by,
            reviewer_id=approval.reviewer_id,
            comment=approval.comment,
            policy_snapshot_json=approval.policy_snapshot,
        )
        self._session.add(record)
        self._session.flush()
        return _approval_to_domain(record)

    def list_approvals(self, model_version_id: UUID) -> list[ModelApproval]:
        records = self._session.scalars(
            select(ModelApprovalModel)
            .where(ModelApprovalModel.model_version_id == model_version_id)
            .order_by(ModelApprovalModel.created_at)
        ).all()
        return [_approval_to_domain(record) for record in records]

    def add_lineage(self, lineage: ModelLineage) -> ModelLineage:
        record = ModelLineageModel(
            id=lineage.id,
            model_version_id=lineage.model_version_id,
            source_type=lineage.source_type,
            source_id=lineage.source_id,
        )
        self._session.add(record)
        self._session.flush()
        return _lineage_to_domain(record)

    def list_lineage(self, model_version_id: UUID) -> list[ModelLineage]:
        records = self._session.scalars(
            select(ModelLineageModel)
            .where(ModelLineageModel.model_version_id == model_version_id)
            .order_by(ModelLineageModel.source_type, ModelLineageModel.source_id)
        ).all()
        return [_lineage_to_domain(record) for record in records]


def _registered_model_to_domain(record: RegisteredModelModel) -> RegisteredModel:
    return RegisteredModel(
        id=record.id,
        organization_id=record.organization_id,
        project_id=record.project_id,
        name=record.name,
        slug=record.slug,
        description=record.description,
        task_type=record.task_type,
        owner_user_id=record.owner_user_id,
        status=RegisteredModelStatus(record.status),
    )


def _model_version_to_domain(record: ModelVersionModel) -> ModelVersion:
    return ModelVersion(
        id=record.id,
        registered_model_id=record.registered_model_id,
        version=record.version,
        training_run_id=record.training_run_id,
        experiment_run_id=record.experiment_run_id,
        artifact_uri=record.artifact_uri,
        model_format=record.model_format,
        signature=record.signature_json,
        metrics={key: float(value) for key, value in record.metrics_json.items()},
        status=ModelVersionStatus(record.status),
        created_by=record.created_by,
    )


def _approval_to_domain(record: ModelApprovalModel) -> ModelApproval:
    return ModelApproval(
        id=record.id,
        model_version_id=record.model_version_id,
        status=ModelApprovalStatus(record.status),
        requested_by=record.requested_by,
        reviewer_id=record.reviewer_id,
        comment=record.comment,
        policy_snapshot=record.policy_snapshot_json,
    )


def _lineage_to_domain(record: ModelLineageModel) -> ModelLineage:
    return ModelLineage(
        id=record.id,
        model_version_id=record.model_version_id,
        source_type=record.source_type,
        source_id=record.source_id,
    )
