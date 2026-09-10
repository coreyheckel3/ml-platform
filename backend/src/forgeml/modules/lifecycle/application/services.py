from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from forgeml.modules.lifecycle.domain.entities import (
    LIFECYCLE_SCHEMA_VERSION,
    ProjectLifecycleDependency,
    ProjectLifecycleMetric,
    ProjectLifecycleSnapshot,
    ProjectLifecycleStage,
    ProjectLifecycleSummary,
)
from forgeml.modules.lifecycle.repositories.interfaces import ProjectLifecycleRepository
from forgeml.platform.domain.errors import PermissionDeniedError, ResourceNotFoundError
from forgeml.platform.security.rbac import Principal


@dataclass(frozen=True)
class GetProjectLifecycleSummaryQuery:
    organization_id: UUID
    project_id: UUID


class ProjectLifecycleService:
    def __init__(self, *, repository: ProjectLifecycleRepository) -> None:
        self._repository = repository

    def get_project_lifecycle_summary(
        self,
        query: GetProjectLifecycleSummaryQuery,
        principal: Principal,
    ) -> ProjectLifecycleSummary:
        if not principal.has("lifecycle:read"):
            raise PermissionDeniedError(
                "You do not have permission to read project lifecycle summaries."
            )
        if str(query.organization_id) != principal.organization_id:
            raise PermissionDeniedError(
                "You cannot read lifecycle summaries for another organization."
            )

        snapshot = self._repository.load_snapshot(
            query.organization_id,
            query.project_id,
        )
        if snapshot is None:
            raise ResourceNotFoundError("Project was not found.")

        stages = _build_stages(snapshot)
        ready_stage_count = sum(1 for stage in stages if stage.status == "ready")
        total_stage_count = len(stages)
        readiness_score = (
            round((ready_stage_count / total_stage_count) * 100)
            if total_stage_count
            else 0
        )
        return ProjectLifecycleSummary(
            schema_version=LIFECYCLE_SCHEMA_VERSION,
            project_id=snapshot.project_id,
            project_name=snapshot.project_name,
            project_slug=snapshot.project_slug,
            project_status=snapshot.project_status,
            readiness_score=readiness_score,
            ready_stage_count=ready_stage_count,
            total_stage_count=total_stage_count,
            stages=stages,
            dependencies=_build_dependencies(stages),
            metrics=_build_metrics(snapshot),
            recommended_actions=_recommended_actions(stages),
            generated_at=datetime.now(UTC),
        )


def _build_stages(snapshot: ProjectLifecycleSnapshot) -> tuple[ProjectLifecycleStage, ...]:
    return (
        ProjectLifecycleStage(
            key="datasets",
            title="Datasets",
            status=_stage_status(
                ready=snapshot.dataset_versions > 0 and snapshot.validation_runs > 0,
                needs_attention=snapshot.datasets > 0 and snapshot.validation_runs == 0,
                pending=snapshot.datasets > 0,
            ),
            description="Raw and versioned data registered for repeatable training.",
            primary_signal=(
                f"{snapshot.dataset_versions} versions, "
                f"{snapshot.validation_runs} validation runs"
            ),
            count=snapshot.dataset_versions,
            last_updated_at=snapshot.last_updated_at,
            route_path="/datasets",
            recommended_action=(
                "Register a dataset version and run schema validation."
                if snapshot.dataset_versions == 0 or snapshot.validation_runs == 0
                else "Keep dataset contracts current as upstream sources evolve."
            ),
        ),
        ProjectLifecycleStage(
            key="feature_store",
            title="Feature Store",
            status=_stage_status(
                ready=snapshot.feature_sets > 0 and snapshot.materializations > 0,
                needs_attention=snapshot.feature_sets > 0 and snapshot.materializations == 0,
                pending=snapshot.feature_sets > 0,
            ),
            description="Reusable feature sets, pipelines, and materializations.",
            primary_signal=(
                f"{snapshot.feature_sets} sets, "
                f"{snapshot.materializations} materializations"
            ),
            count=snapshot.feature_sets,
            last_updated_at=snapshot.last_updated_at,
            route_path="/feature-store",
            recommended_action=(
                "Materialize at least one feature set before production training."
                if snapshot.feature_sets > 0 and snapshot.materializations == 0
                else "Create a feature set and pipeline for reusable training inputs."
                if snapshot.feature_sets == 0
                else "Monitor materialization freshness and feature lineage."
            ),
        ),
        ProjectLifecycleStage(
            key="experiments",
            title="Experiments",
            status=_stage_status(
                ready=snapshot.experiment_runs > 0,
                needs_attention=snapshot.experiments > 0 and snapshot.experiment_runs == 0,
                pending=snapshot.experiments > 0,
            ),
            description="Tracked hypotheses, parameters, metrics, and artifacts.",
            primary_signal=f"{snapshot.experiment_runs} tracked runs",
            count=snapshot.experiment_runs,
            last_updated_at=snapshot.last_updated_at,
            route_path="/experiments",
            recommended_action=(
                "Start an experiment run with logged parameters and metrics."
                if snapshot.experiment_runs == 0
                else "Compare top runs against the target business metric."
            ),
        ),
        ProjectLifecycleStage(
            key="training",
            title="Training",
            status=_stage_status(
                ready=snapshot.succeeded_training_runs > 0,
                needs_attention=snapshot.training_runs > 0
                and snapshot.succeeded_training_runs == 0,
                pending=snapshot.training_runs > 0,
            ),
            description="Queued and executed training jobs with reproducible inputs.",
            primary_signal=(
                f"{snapshot.succeeded_training_runs} succeeded, "
                f"{snapshot.failed_training_runs} failed"
            ),
            count=snapshot.training_runs,
            last_updated_at=snapshot.last_updated_at,
            route_path="/training-runs",
            recommended_action=(
                "Run the training worker until at least one training run succeeds."
                if snapshot.succeeded_training_runs == 0
                else "Promote the best successful run into the model registry."
            ),
        ),
        ProjectLifecycleStage(
            key="model_registry",
            title="Model Registry",
            status=_stage_status(
                ready=snapshot.model_versions > 0 and snapshot.approved_model_versions > 0,
                needs_attention=snapshot.model_versions > 0
                and snapshot.approved_model_versions == 0,
                pending=snapshot.registered_models > 0,
            ),
            description="Versioned model artifacts with approval state and lineage.",
            primary_signal=(
                f"{snapshot.model_versions} versions, "
                f"{snapshot.approved_model_versions} approved"
            ),
            count=snapshot.model_versions,
            last_updated_at=snapshot.last_updated_at,
            route_path="/models",
            recommended_action=(
                "Request or complete approval for a model version."
                if snapshot.model_versions > 0 and snapshot.approved_model_versions == 0
                else "Register a model version from a successful training run."
                if snapshot.model_versions == 0
                else "Keep model lineage and approval metadata attached."
            ),
        ),
        ProjectLifecycleStage(
            key="deployment",
            title="Deployment",
            status=_stage_status(
                ready=snapshot.active_deployments > 0,
                needs_attention=snapshot.deployments > 0 and snapshot.active_deployments == 0,
                pending=snapshot.deployments > 0,
            ),
            description="Serving revisions, traffic policy, health checks, and rollback paths.",
            primary_signal=(
                f"{snapshot.active_deployments} active of "
                f"{snapshot.deployments} deployments"
            ),
            count=snapshot.deployments,
            last_updated_at=snapshot.last_updated_at,
            route_path="/deployments",
            recommended_action=(
                "Deploy an approved model version to a serving environment."
                if snapshot.deployments == 0
                else "Activate or roll back the serving revision before exposing traffic."
                if snapshot.active_deployments == 0
                else "Validate health probes and rollback evidence after each release."
            ),
        ),
        ProjectLifecycleStage(
            key="inference",
            title="Inference",
            status=_stage_status(
                ready=snapshot.active_inference_endpoints > 0 and snapshot.prediction_count > 0,
                needs_attention=snapshot.active_inference_endpoints > 0
                and snapshot.prediction_count == 0,
                pending=snapshot.inference_endpoints > 0,
            ),
            description="Online prediction endpoints and request telemetry.",
            primary_signal=(
                f"{snapshot.prediction_count} predictions, "
                f"{snapshot.inference_error_count} errors"
            ),
            count=snapshot.inference_endpoints,
            last_updated_at=snapshot.last_updated_at,
            route_path="/inference",
            recommended_action=(
                "Create an inference endpoint and send a smoke prediction."
                if snapshot.inference_endpoints == 0
                else "Run a smoke prediction to populate endpoint telemetry."
                if snapshot.prediction_count == 0
                else "Track latency and error budgets by endpoint."
            ),
        ),
        ProjectLifecycleStage(
            key="monitoring",
            title="Monitoring",
            status=_stage_status(
                ready=snapshot.prediction_count > 0 and snapshot.alert_rules > 0,
                needs_attention=snapshot.prediction_count > 0 and snapshot.alert_rules == 0,
                pending=snapshot.prediction_count > 0,
            ),
            description="Operational dashboards, latency, errors, and alert pressure.",
            primary_signal=(
                f"{snapshot.alert_rules} rules, "
                f"{snapshot.active_alert_events} active alerts"
            ),
            count=snapshot.alert_rules,
            last_updated_at=snapshot.last_updated_at,
            route_path="/monitoring",
            recommended_action=(
                "Create alert rules for latency, error rate, and drift thresholds."
                if snapshot.alert_rules == 0
                else "Triage active alerts and watch p95 latency trends."
            ),
        ),
        ProjectLifecycleStage(
            key="drift_detection",
            title="Drift Detection",
            status=_stage_status(
                ready=snapshot.drift_profiles > 0 and snapshot.drift_reports > 0,
                needs_attention=snapshot.drift_profiles > 0 and snapshot.drift_reports == 0,
                pending=snapshot.drift_profiles > 0,
            ),
            description="Baseline profiles and feature-level drift reports.",
            primary_signal=(
                f"{snapshot.drift_reports} reports, "
                f"{snapshot.breached_drift_reports} threshold breaches"
            ),
            count=snapshot.drift_reports,
            last_updated_at=snapshot.last_updated_at,
            route_path="/drift",
            recommended_action=(
                "Create a drift baseline and run a report from endpoint traffic."
                if snapshot.drift_profiles == 0
                else "Run a drift report against the latest production window."
                if snapshot.drift_reports == 0
                else "Review breached drift reports before approving retraining."
            ),
        ),
        ProjectLifecycleStage(
            key="retraining",
            title="Retraining",
            status=_stage_status(
                ready=snapshot.enabled_retraining_policies > 0
                and snapshot.successful_retraining_runs > 0,
                needs_attention=snapshot.retraining_policies > 0
                and snapshot.enabled_retraining_policies == 0,
                pending=snapshot.retraining_policies > 0,
            ),
            description="Automatic retraining policies and approval-aware run history.",
            primary_signal=(
                f"{snapshot.enabled_retraining_policies} enabled policies, "
                f"{snapshot.queued_retraining_runs} queued runs"
            ),
            count=snapshot.retraining_runs,
            last_updated_at=snapshot.last_updated_at,
            route_path="/retraining",
            recommended_action=(
                "Enable a retraining policy after deployment and drift checks exist."
                if snapshot.retraining_policies == 0
                else "Approve or execute queued retraining runs to close the loop."
                if snapshot.successful_retraining_runs == 0
                else "Review retraining outcomes before promoting refreshed models."
            ),
        ),
    )


def _stage_status(*, ready: bool, needs_attention: bool, pending: bool) -> str:
    if ready:
        return "ready"
    if needs_attention:
        return "needs_attention"
    if pending:
        return "pending"
    return "missing"


def _build_dependencies(
    stages: tuple[ProjectLifecycleStage, ...],
) -> tuple[ProjectLifecycleDependency, ...]:
    stage_by_key = {stage.key: stage for stage in stages}
    edges = (
        ("datasets", "feature_store"),
        ("feature_store", "experiments"),
        ("experiments", "training"),
        ("training", "model_registry"),
        ("model_registry", "deployment"),
        ("deployment", "inference"),
        ("inference", "monitoring"),
        ("monitoring", "drift_detection"),
        ("drift_detection", "retraining"),
    )
    dependencies: list[ProjectLifecycleDependency] = []
    for source, target in edges:
        source_stage = stage_by_key[source]
        target_stage = stage_by_key[target]
        healthy = source_stage.status == "ready" and target_stage.status in {
            "ready",
            "pending",
            "needs_attention",
        }
        dependencies.append(
            ProjectLifecycleDependency(
                source_stage=source,
                target_stage=target,
                status="connected" if healthy else "blocked",
                detail=(
                    f"{source_stage.title} feeds {target_stage.title}."
                    if healthy
                    else f"{target_stage.title} needs {source_stage.title.lower()} evidence."
                ),
            )
        )
    return tuple(dependencies)


def _build_metrics(
    snapshot: ProjectLifecycleSnapshot,
) -> tuple[ProjectLifecycleMetric, ...]:
    error_rate = (
        snapshot.inference_error_count / snapshot.prediction_count
        if snapshot.prediction_count
        else 0.0
    )
    return (
        ProjectLifecycleMetric(
            label="Dataset Versions",
            value=str(snapshot.dataset_versions),
            detail=f"{snapshot.validation_runs} validation runs",
            tone="success" if snapshot.validation_runs else "warning",
        ),
        ProjectLifecycleMetric(
            label="Successful Training",
            value=str(snapshot.succeeded_training_runs),
            detail=f"{snapshot.training_runs} total runs",
            tone="success" if snapshot.succeeded_training_runs else "warning",
        ),
        ProjectLifecycleMetric(
            label="Approved Models",
            value=str(snapshot.approved_model_versions),
            detail=f"{snapshot.model_versions} model versions",
            tone="success" if snapshot.approved_model_versions else "warning",
        ),
        ProjectLifecycleMetric(
            label="Predictions",
            value=str(snapshot.prediction_count),
            detail=f"{error_rate:.2%} error rate",
            tone="danger" if error_rate > 0.05 else "success",
        ),
        ProjectLifecycleMetric(
            label="Drift Breaches",
            value=str(snapshot.breached_drift_reports),
            detail=f"{snapshot.drift_reports} reports",
            tone="warning" if snapshot.breached_drift_reports else "success",
        ),
        ProjectLifecycleMetric(
            label="Retraining Runs",
            value=str(snapshot.retraining_runs),
            detail=f"{snapshot.successful_retraining_runs} succeeded",
            tone="success" if snapshot.successful_retraining_runs else "warning",
        ),
    )


def _recommended_actions(
    stages: tuple[ProjectLifecycleStage, ...],
) -> tuple[str, ...]:
    return tuple(
        stage.recommended_action
        for stage in stages
        if stage.status in {"missing", "pending", "needs_attention"}
    )[:4]
