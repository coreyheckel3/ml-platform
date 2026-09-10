from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from forgeml.modules.evaluation.domain.entities import (
    EvaluationCandidate,
    EvaluationComparisonSnapshot,
    EvaluationModelEvidence,
)
from forgeml.modules.experiments.infrastructure.sqlalchemy_models import (
    ExperimentModel,
    ExperimentRunModel,
)
from forgeml.modules.model_registry.infrastructure.sqlalchemy_models import (
    ModelApprovalModel,
    ModelLineageModel,
    ModelVersionModel,
    RegisteredModelModel,
)
from forgeml.modules.projects.infrastructure.sqlalchemy_models import ProjectModel
from forgeml.modules.training.infrastructure.sqlalchemy_models import TrainingRunModel


class SqlAlchemyEvaluationComparisonRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def load_snapshot(
        self,
        organization_id: UUID,
        project_id: UUID,
    ) -> EvaluationComparisonSnapshot | None:
        project = self._session.scalar(
            select(ProjectModel).where(
                ProjectModel.id == project_id,
                ProjectModel.organization_id == organization_id,
            )
        )
        if project is None:
            return None

        training_runs = self._session.scalars(
            select(TrainingRunModel)
            .where(
                TrainingRunModel.organization_id == organization_id,
                TrainingRunModel.project_id == project_id,
            )
            .order_by(TrainingRunModel.updated_at.desc())
        ).all()
        training_by_experiment_run = _latest_training_runs(training_runs)

        model_rows = self._session.execute(
            select(ModelVersionModel, RegisteredModelModel)
            .join(
                RegisteredModelModel,
                RegisteredModelModel.id == ModelVersionModel.registered_model_id,
            )
            .where(
                RegisteredModelModel.organization_id == organization_id,
                RegisteredModelModel.project_id == project_id,
            )
            .order_by(ModelVersionModel.version.desc())
        ).all()
        version_ids = [version.id for version, _ in model_rows]
        approvals = self._load_approvals(version_ids)
        lineage = self._load_lineage(version_ids)
        version_by_experiment_run = _latest_model_versions(model_rows)

        experiment_rows = self._session.execute(
            select(ExperimentRunModel, ExperimentModel.name)
            .join(ExperimentModel, ExperimentModel.id == ExperimentRunModel.experiment_id)
            .where(
                ExperimentModel.organization_id == organization_id,
                ExperimentModel.project_id == project_id,
                ExperimentRunModel.project_id == project_id,
            )
            .order_by(ExperimentRunModel.updated_at.desc())
        ).all()
        candidates = tuple(
            _candidate_from_row(
                experiment_run,
                experiment_name,
                training_by_experiment_run.get(experiment_run.id),
                version_by_experiment_run.get(experiment_run.id),
                approvals,
            )
            for experiment_run, experiment_name in experiment_rows
        )

        model_evidence = tuple(
            _model_evidence_from_row(version, registered_model, approvals, lineage)
            for version, registered_model in model_rows
        )
        return EvaluationComparisonSnapshot(
            project_id=project.id,
            project_name=project.name,
            project_slug=project.slug,
            project_status=project.status,
            candidates=candidates,
            model_evidence=model_evidence,
        )

    def _load_approvals(
        self,
        version_ids: Iterable[UUID],
    ) -> dict[UUID, list[ModelApprovalModel]]:
        ids = tuple(version_ids)
        if not ids:
            return {}
        rows = self._session.scalars(
            select(ModelApprovalModel)
            .where(ModelApprovalModel.model_version_id.in_(ids))
            .order_by(ModelApprovalModel.created_at.desc())
        ).all()
        approvals: dict[UUID, list[ModelApprovalModel]] = defaultdict(list)
        for approval in rows:
            approvals[approval.model_version_id].append(approval)
        return dict(approvals)

    def _load_lineage(
        self,
        version_ids: Iterable[UUID],
    ) -> dict[UUID, list[ModelLineageModel]]:
        ids = tuple(version_ids)
        if not ids:
            return {}
        rows = self._session.scalars(
            select(ModelLineageModel)
            .where(ModelLineageModel.model_version_id.in_(ids))
            .order_by(ModelLineageModel.source_type, ModelLineageModel.source_id)
        ).all()
        lineage: dict[UUID, list[ModelLineageModel]] = defaultdict(list)
        for entry in rows:
            lineage[entry.model_version_id].append(entry)
        return dict(lineage)


def _latest_training_runs(
    training_runs: Iterable[TrainingRunModel],
) -> dict[UUID, TrainingRunModel]:
    latest: dict[UUID, TrainingRunModel] = {}
    for training_run in training_runs:
        latest.setdefault(training_run.experiment_run_id, training_run)
    return latest


def _latest_model_versions(
    model_rows: Iterable[tuple[ModelVersionModel, RegisteredModelModel]],
) -> dict[UUID, tuple[ModelVersionModel, RegisteredModelModel]]:
    latest: dict[UUID, tuple[ModelVersionModel, RegisteredModelModel]] = {}
    for version, registered_model in model_rows:
        latest.setdefault(version.experiment_run_id, (version, registered_model))
    return latest


def _candidate_from_row(
    experiment_run: ExperimentRunModel,
    experiment_name: str,
    training_run: TrainingRunModel | None,
    version_info: tuple[ModelVersionModel, RegisteredModelModel] | None,
    approvals: dict[UUID, list[ModelApprovalModel]],
) -> EvaluationCandidate:
    model_version: ModelVersionModel | None = None
    registered_model: RegisteredModelModel | None = None
    if version_info is not None:
        model_version, registered_model = version_info

    metrics = _merge_metrics(
        _numeric_record(experiment_run.metrics_json),
        _numeric_record(training_run.metrics_json) if training_run else {},
        _numeric_record(model_version.metrics_json) if model_version else {},
    )
    return EvaluationCandidate(
        experiment_id=experiment_run.experiment_id,
        experiment_name=experiment_name,
        experiment_run_id=experiment_run.id,
        run_name=experiment_run.run_name,
        status=training_run.status if training_run else experiment_run.status,
        model_type=training_run.model_type if training_run else experiment_run.model_type,
        training_run_id=training_run.id if training_run else None,
        model_version_id=model_version.id if model_version else None,
        registered_model_name=registered_model.name if registered_model else None,
        model_version=model_version.version if model_version else None,
        model_version_status=model_version.status if model_version else None,
        approval_status=_approval_status(
            model_version,
            approvals.get(model_version.id, []) if model_version else [],
        ),
        objective_metric_name=training_run.objective_metric_name if training_run else None,
        metrics=metrics,
        parameters=_object_record(experiment_run.parameters_json),
        evaluation_report=_object_record(experiment_run.evaluation_report_json),
        dataset_version_id=experiment_run.dataset_version_id,
        feature_set_id=experiment_run.feature_set_id,
        artifact_uri=(
            model_version.artifact_uri
            if model_version
            else training_run.artifact_uri
            if training_run
            else experiment_run.artifact_uri
        ),
        artifact_manifest_uri=model_version.artifact_manifest_uri if model_version else "",
        artifact_manifest_hash=model_version.artifact_manifest_hash if model_version else "",
        created_at=experiment_run.created_at,
        updated_at=experiment_run.updated_at,
    )


def _model_evidence_from_row(
    version: ModelVersionModel,
    registered_model: RegisteredModelModel,
    approvals: dict[UUID, list[ModelApprovalModel]],
    lineage: dict[UUID, list[ModelLineageModel]],
) -> EvaluationModelEvidence:
    return EvaluationModelEvidence(
        registered_model_id=registered_model.id,
        registered_model_name=registered_model.name,
        model_version_id=version.id,
        version=version.version,
        status=version.status,
        approval_status=_approval_status(version, approvals.get(version.id, [])),
        model_format=version.model_format,
        signature=_object_record(version.signature_json),
        metrics=_numeric_record(version.metrics_json),
        artifact_uri=version.artifact_uri,
        artifact_manifest_uri=version.artifact_manifest_uri,
        artifact_manifest_hash=version.artifact_manifest_hash,
        lineage_sources=tuple(
            f"{entry.source_type}:{entry.source_id}" for entry in lineage.get(version.id, [])
        ),
        training_run_id=version.training_run_id,
        experiment_run_id=version.experiment_run_id,
    )


def _approval_status(
    version: ModelVersionModel | None,
    approvals: Iterable[ModelApprovalModel],
) -> str:
    if version is None:
        return "not_registered"
    for approval in approvals:
        if approval.status in {"approved", "rejected", "requested"}:
            return approval.status
    if version.status == "approved":
        return "approved"
    if version.status == "rejected":
        return "rejected"
    if version.status == "pending_approval":
        return "requested"
    return "not_requested"


def _merge_metrics(*metric_sets: dict[str, float]) -> dict[str, float]:
    merged: dict[str, float] = {}
    for metric_set in metric_sets:
        merged.update(metric_set)
    return merged


def _numeric_record(value: object) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    metrics: dict[str, float] = {}
    for key, raw_value in value.items():
        if isinstance(key, str) and isinstance(raw_value, int | float):
            metrics[key] = float(raw_value)
    return metrics


def _object_record(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in value.items()}
