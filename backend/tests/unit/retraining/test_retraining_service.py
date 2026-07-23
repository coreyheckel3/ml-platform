from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from forgeml.modules.retraining.application.services import (
    CreateRetrainingPolicyCommand,
    EvaluateRetrainingPolicyCommand,
    RetrainingService,
    TriggerRetrainingRunCommand,
)
from forgeml.modules.retraining.domain.entities import (
    AlertRetrainingSignal,
    DriftRetrainingSignal,
    RetrainingDecision,
    RetrainingPolicy,
    RetrainingRun,
    RetrainingRunStatus,
    RetrainingTrainingLaunch,
    RetrainingTrainingRequest,
)
from forgeml.platform.security.rbac import Principal


class FakeRetrainingRepository:
    def __init__(self) -> None:
        self.policies: dict[UUID, RetrainingPolicy] = {}
        self.runs: dict[UUID, RetrainingRun] = {}
        self.deployments: set[tuple[UUID, UUID, UUID]] = set()
        self.experiments: set[tuple[UUID, UUID, UUID]] = set()
        self.dataset_versions: set[tuple[UUID, UUID]] = set()
        self.feature_sets: set[tuple[UUID, UUID]] = set()
        self.drift_signals: dict[UUID, DriftRetrainingSignal] = {}
        self.alert_signals: dict[UUID, AlertRetrainingSignal] = {}

    def add_policy(self, policy: RetrainingPolicy) -> RetrainingPolicy:
        self.policies[policy.id] = policy
        return policy

    def get_policy(self, policy_id: UUID) -> RetrainingPolicy | None:
        return self.policies.get(policy_id)

    def list_policies(self, organization_id: UUID, project_id: UUID) -> list[RetrainingPolicy]:
        return [
            policy
            for policy in self.policies.values()
            if policy.organization_id == organization_id and policy.project_id == project_id
        ]

    def policy_slug_exists(self, organization_id: UUID, project_id: UUID, slug: str) -> bool:
        return any(
            policy.organization_id == organization_id
            and policy.project_id == project_id
            and policy.slug == slug
            for policy in self.policies.values()
        )

    def add_run(self, run: RetrainingRun) -> RetrainingRun:
        saved = replace(
            run,
            created_at=run.created_at or datetime.now(tz=UTC),
            updated_at=run.updated_at or datetime.now(tz=UTC),
        )
        self.runs[saved.id] = saved
        return saved

    def get_run(self, run_id: UUID) -> RetrainingRun | None:
        return self.runs.get(run_id)

    def update_run(self, run: RetrainingRun) -> RetrainingRun:
        saved = replace(run, updated_at=datetime.now(tz=UTC))
        self.runs[saved.id] = saved
        return saved

    def list_runs(self, organization_id: UUID, project_id: UUID) -> list[RetrainingRun]:
        return [
            run
            for run in self.runs.values()
            if run.organization_id == organization_id and run.project_id == project_id
        ]

    def get_existing_run_for_trigger(
        self,
        policy_id: UUID,
        drift_report_id: UUID | None,
        alert_event_id: UUID | None,
    ) -> RetrainingRun | None:
        for run in self.runs.values():
            if run.policy_id != policy_id:
                continue
            if drift_report_id is not None and run.drift_report_id == drift_report_id:
                return run
            if alert_event_id is not None and run.alert_event_id == alert_event_id:
                return run
        return None

    def latest_run_created_at(self, policy_id: UUID) -> datetime | None:
        created_at_values = [
            run.created_at
            for run in self.runs.values()
            if run.policy_id == policy_id
            and run.status in {RetrainingRunStatus.PENDING_APPROVAL, RetrainingRunStatus.QUEUED}
            and run.created_at is not None
        ]
        return max(created_at_values) if created_at_values else None

    def count_runs_since(self, policy_id: UUID, since: datetime) -> int:
        return sum(
            1
            for run in self.runs.values()
            if run.policy_id == policy_id
            and run.status in {RetrainingRunStatus.PENDING_APPROVAL, RetrainingRunStatus.QUEUED}
            and run.created_at is not None
            and run.created_at >= since
        )

    def deployment_belongs_to_project(
        self,
        organization_id: UUID,
        project_id: UUID,
        deployment_id: UUID,
    ) -> bool:
        return (organization_id, project_id, deployment_id) in self.deployments

    def experiment_belongs_to_project(
        self,
        organization_id: UUID,
        project_id: UUID,
        experiment_id: UUID,
    ) -> bool:
        return (organization_id, project_id, experiment_id) in self.experiments

    def dataset_version_belongs_to_project(self, project_id: UUID, version_id: UUID) -> bool:
        return (project_id, version_id) in self.dataset_versions

    def feature_set_belongs_to_project(self, project_id: UUID, feature_set_id: UUID) -> bool:
        return (project_id, feature_set_id) in self.feature_sets

    def get_drift_signal(self, drift_report_id: UUID) -> DriftRetrainingSignal | None:
        return self.drift_signals.get(drift_report_id)

    def get_alert_signal(self, alert_event_id: UUID) -> AlertRetrainingSignal | None:
        return self.alert_signals.get(alert_event_id)


class FakeTrainingLauncher:
    def __init__(self) -> None:
        self.requests: list[RetrainingTrainingRequest] = []

    def launch_training_run(
        self,
        request: RetrainingTrainingRequest,
        principal: Principal,
    ) -> RetrainingTrainingLaunch:
        self.requests.append(request)
        return RetrainingTrainingLaunch(
            training_run_id=uuid4(),
            status="queued",
            orchestrator_run_id=f"workflow:{request.run_name}",
        )


def principal(organization_id: UUID, user_id: UUID) -> Principal:
    return Principal(
        user_id=str(user_id),
        email="owner@example.com",
        organization_id=str(organization_id),
        permissions=frozenset({"*"}),
    )


def test_retraining_service_queues_drift_triggered_training_run() -> None:
    repository = FakeRetrainingRepository()
    launcher = FakeTrainingLauncher()
    service = RetrainingService(repository=repository, training_launcher=launcher)
    organization_id = uuid4()
    project_id = uuid4()
    deployment_id = uuid4()
    experiment_id = uuid4()
    dataset_version_id = uuid4()
    user_id = uuid4()
    drift_report_id = uuid4()
    repository.deployments.add((organization_id, project_id, deployment_id))
    repository.experiments.add((organization_id, project_id, experiment_id))
    repository.dataset_versions.add((project_id, dataset_version_id))
    repository.drift_signals[drift_report_id] = DriftRetrainingSignal(
        drift_report_id=drift_report_id,
        organization_id=organization_id,
        project_id=project_id,
        deployment_id=deployment_id,
        endpoint_id=uuid4(),
        drift_score=0.42,
        drifted_feature_count=3,
        evaluated_feature_count=5,
        status="completed",
    )
    actor = principal(organization_id, user_id)

    policy = service.create_policy(
        _create_policy_command(
            organization_id,
            project_id,
            deployment_id,
            experiment_id,
            dataset_version_id,
            user_id,
            approval_required=False,
        ),
        actor,
    )
    evaluation = service.evaluate_policy(
        EvaluateRetrainingPolicyCommand(
            policy_id=policy.id,
            drift_report_id=drift_report_id,
            alert_event_id=None,
            reason="Nightly drift evaluation.",
        ),
        actor,
    )

    assert evaluation.decision == RetrainingDecision.TRIGGERED
    assert evaluation.run is not None
    assert evaluation.run.status == RetrainingRunStatus.QUEUED
    assert evaluation.run.training_run_id is not None
    assert launcher.requests[0].experiment_id == experiment_id
    assert launcher.requests[0].run_name.startswith("fraud-retrain-drift-")


def test_retraining_service_holds_run_for_approval_then_launches() -> None:
    repository = FakeRetrainingRepository()
    launcher = FakeTrainingLauncher()
    service = RetrainingService(repository=repository, training_launcher=launcher)
    organization_id = uuid4()
    project_id = uuid4()
    deployment_id = uuid4()
    experiment_id = uuid4()
    dataset_version_id = uuid4()
    user_id = uuid4()
    repository.deployments.add((organization_id, project_id, deployment_id))
    repository.experiments.add((organization_id, project_id, experiment_id))
    repository.dataset_versions.add((project_id, dataset_version_id))
    actor = principal(organization_id, user_id)

    policy = service.create_policy(
        _create_policy_command(
            organization_id,
            project_id,
            deployment_id,
            experiment_id,
            dataset_version_id,
            user_id,
            approval_required=True,
        ),
        actor,
    )
    evaluation = service.trigger_run(command=_manual_command(policy.id), principal=actor)
    approved = service.approve_run(evaluation.run.id, actor) if evaluation.run else None

    assert evaluation.decision == RetrainingDecision.PENDING_APPROVAL
    assert approved is not None
    assert approved.status == RetrainingRunStatus.QUEUED
    assert approved.approved_by == user_id
    assert len(launcher.requests) == 1


def test_retraining_service_skips_duplicate_drift_trigger() -> None:
    repository = FakeRetrainingRepository()
    launcher = FakeTrainingLauncher()
    service = RetrainingService(repository=repository, training_launcher=launcher)
    organization_id = uuid4()
    project_id = uuid4()
    deployment_id = uuid4()
    experiment_id = uuid4()
    dataset_version_id = uuid4()
    user_id = uuid4()
    drift_report_id = uuid4()
    repository.deployments.add((organization_id, project_id, deployment_id))
    repository.experiments.add((organization_id, project_id, experiment_id))
    repository.dataset_versions.add((project_id, dataset_version_id))
    repository.drift_signals[drift_report_id] = DriftRetrainingSignal(
        drift_report_id=drift_report_id,
        organization_id=organization_id,
        project_id=project_id,
        deployment_id=deployment_id,
        endpoint_id=uuid4(),
        drift_score=0.42,
        drifted_feature_count=3,
        evaluated_feature_count=5,
        status="completed",
    )
    actor = principal(organization_id, user_id)
    policy = service.create_policy(
        _create_policy_command(
            organization_id,
            project_id,
            deployment_id,
            experiment_id,
            dataset_version_id,
            user_id,
            approval_required=False,
        ),
        actor,
    )
    command = EvaluateRetrainingPolicyCommand(
        policy_id=policy.id,
        drift_report_id=drift_report_id,
        alert_event_id=None,
        reason="Nightly drift evaluation.",
    )

    service.evaluate_policy(command, actor)
    duplicate = service.evaluate_policy(command, actor)

    assert duplicate.decision == RetrainingDecision.SKIPPED
    assert duplicate.triggered is False
    assert len(launcher.requests) == 1


def _create_policy_command(
    organization_id: UUID,
    project_id: UUID,
    deployment_id: UUID,
    experiment_id: UUID,
    dataset_version_id: UUID,
    user_id: UUID,
    *,
    approval_required: bool,
) -> CreateRetrainingPolicyCommand:
    return CreateRetrainingPolicyCommand(
        organization_id=organization_id,
        project_id=project_id,
        deployment_id=deployment_id,
        name="Fraud Drift Retraining",
        description="Retrain fraud model when drift breaches thresholds.",
        trigger_type="drift",
        trigger_config={"min_drift_score": 0.2, "min_drifted_features": 1},
        training_template={
            "experiment_id": str(experiment_id),
            "dataset_version_id": str(dataset_version_id),
            "run_name_prefix": "fraud-retrain",
            "algorithm": "xgboost",
            "model_type": "xgboost",
            "objective_metric_name": "auc",
            "hyperparameters": {"max_depth": 6},
        },
        cooldown_seconds=0,
        max_runs_per_day=5,
        approval_required=approval_required,
        enabled=True,
        created_by=user_id,
    )


def _manual_command(policy_id: UUID) -> TriggerRetrainingRunCommand:
    return TriggerRetrainingRunCommand(policy_id=policy_id, reason="Operator requested retraining.")
