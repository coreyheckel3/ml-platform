from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from forgeml.modules.retraining.domain.entities import (
    AlertRetrainingSignal,
    DriftRetrainingSignal,
    RetrainingDecision,
    RetrainingEvaluation,
    RetrainingPolicy,
    RetrainingPolicyStatus,
    RetrainingRun,
    RetrainingRunStatus,
    RetrainingTrainingRequest,
    RetrainingTriggerType,
)
from forgeml.modules.retraining.domain.policies import (
    build_retraining_policy_slug,
    normalize_training_template,
    normalize_trigger_config,
    parse_retraining_trigger_type,
    retraining_policy_accepts_alert,
    retraining_policy_accepts_drift,
    retraining_policy_is_active,
    validate_retraining_cooldown_seconds,
    validate_retraining_max_runs_per_day,
    validate_retraining_policy_name,
)
from forgeml.modules.retraining.repositories.interfaces import (
    RetrainingRepository,
    TrainingRunLauncher,
)
from forgeml.platform.domain.errors import (
    ConflictError,
    DomainValidationError,
    PermissionDeniedError,
    ResourceNotFoundError,
)
from forgeml.platform.security.rbac import Principal


@dataclass(frozen=True)
class CreateRetrainingPolicyCommand:
    organization_id: UUID
    project_id: UUID
    deployment_id: UUID
    name: str
    description: str
    trigger_type: str
    trigger_config: dict[str, object]
    training_template: dict[str, object]
    cooldown_seconds: int
    max_runs_per_day: int
    approval_required: bool
    enabled: bool
    created_by: UUID


@dataclass(frozen=True)
class EvaluateRetrainingPolicyCommand:
    policy_id: UUID
    drift_report_id: UUID | None
    alert_event_id: UUID | None
    reason: str


@dataclass(frozen=True)
class TriggerRetrainingRunCommand:
    policy_id: UUID
    reason: str


class RetrainingService:
    def __init__(
        self,
        *,
        repository: RetrainingRepository,
        training_launcher: TrainingRunLauncher,
    ) -> None:
        self._repository = repository
        self._training_launcher = training_launcher

    def create_policy(
        self,
        command: CreateRetrainingPolicyCommand,
        principal: Principal,
    ) -> RetrainingPolicy:
        self._require(principal, "retraining_policies:create")
        self._require_same_organization(command.organization_id, principal)
        validate_retraining_policy_name(command.name)
        trigger_type = parse_retraining_trigger_type(command.trigger_type)
        trigger_config = normalize_trigger_config(trigger_type, command.trigger_config)
        training_template = normalize_training_template(command.training_template)
        validate_retraining_cooldown_seconds(command.cooldown_seconds)
        validate_retraining_max_runs_per_day(command.max_runs_per_day)
        slug = build_retraining_policy_slug(command.name)
        if self._repository.policy_slug_exists(
            command.organization_id,
            command.project_id,
            slug,
        ):
            raise ConflictError("A retraining policy with this name already exists.")
        if not self._repository.deployment_belongs_to_project(
            command.organization_id,
            command.project_id,
            command.deployment_id,
        ):
            raise ResourceNotFoundError("Deployment was not found.")
        self._validate_training_references(command, training_template)

        policy = RetrainingPolicy(
            id=uuid4(),
            organization_id=command.organization_id,
            project_id=command.project_id,
            deployment_id=command.deployment_id,
            name=command.name.strip(),
            slug=slug,
            description=command.description.strip(),
            trigger_type=trigger_type,
            trigger_config=trigger_config,
            training_template=training_template,
            cooldown_seconds=command.cooldown_seconds,
            max_runs_per_day=command.max_runs_per_day,
            approval_required=command.approval_required,
            enabled=command.enabled,
            status=RetrainingPolicyStatus.ACTIVE,
            created_by=command.created_by,
        )
        return self._repository.add_policy(policy)

    def list_policies(
        self,
        project_id: UUID,
        principal: Principal,
    ) -> list[RetrainingPolicy]:
        self._require(principal, "retraining_policies:read")
        return self._repository.list_policies(UUID(principal.organization_id), project_id)

    def evaluate_policy(
        self,
        command: EvaluateRetrainingPolicyCommand,
        principal: Principal,
    ) -> RetrainingEvaluation:
        self._require(principal, "retraining_runs:create")
        policy = self._get_scoped_policy(command.policy_id, principal)
        source = self._load_policy_source(policy, command)
        return self._evaluate_and_maybe_launch(
            policy,
            principal,
            reason=command.reason.strip() or "Retraining policy was evaluated.",
            drift_signal=source[0],
            alert_signal=source[1],
            manual_override=False,
        )

    def trigger_run(
        self,
        command: TriggerRetrainingRunCommand,
        principal: Principal,
    ) -> RetrainingEvaluation:
        self._require(principal, "retraining_runs:create")
        policy = self._get_scoped_policy(command.policy_id, principal)
        return self._evaluate_and_maybe_launch(
            policy,
            principal,
            reason=command.reason.strip() or "Manual retraining run was requested.",
            drift_signal=None,
            alert_signal=None,
            manual_override=True,
        )

    def list_runs(self, project_id: UUID, principal: Principal) -> list[RetrainingRun]:
        self._require(principal, "retraining_runs:read")
        return self._repository.list_runs(UUID(principal.organization_id), project_id)

    def get_run(self, run_id: UUID, principal: Principal) -> RetrainingRun:
        self._require(principal, "retraining_runs:read")
        return self._get_scoped_run(run_id, principal)

    def approve_run(self, run_id: UUID, principal: Principal) -> RetrainingRun:
        self._require(principal, "retraining_runs:approve")
        run = self._get_scoped_run(run_id, principal)
        if run.status != RetrainingRunStatus.PENDING_APPROVAL:
            raise DomainValidationError("Only pending retraining runs can be approved.")
        request = self._training_request_from_config(run.training_config, run.requested_by)
        launch = self._training_launcher.launch_training_run(request, principal)
        updated = replace(
            run,
            training_run_id=launch.training_run_id,
            status=RetrainingRunStatus.QUEUED,
            approved_by=UUID(principal.user_id),
            decision_metadata={
                **run.decision_metadata,
                "approved_by": principal.user_id,
                "training_status": launch.status,
                "orchestrator_run_id": launch.orchestrator_run_id,
            },
        )
        return self._repository.update_run(updated)

    def reject_run(self, run_id: UUID, principal: Principal) -> RetrainingRun:
        self._require(principal, "retraining_runs:reject")
        run = self._get_scoped_run(run_id, principal)
        if run.status != RetrainingRunStatus.PENDING_APPROVAL:
            raise DomainValidationError("Only pending retraining runs can be rejected.")
        updated = replace(
            run,
            status=RetrainingRunStatus.REJECTED,
            rejected_by=UUID(principal.user_id),
            decision_metadata={**run.decision_metadata, "rejected_by": principal.user_id},
        )
        return self._repository.update_run(updated)

    def _evaluate_and_maybe_launch(
        self,
        policy: RetrainingPolicy,
        principal: Principal,
        *,
        reason: str,
        drift_signal: DriftRetrainingSignal | None,
        alert_signal: AlertRetrainingSignal | None,
        manual_override: bool,
    ) -> RetrainingEvaluation:
        active, active_reason = retraining_policy_is_active(policy)
        trigger_type = RetrainingTriggerType.MANUAL if manual_override else policy.trigger_type
        if not active:
            return self._skip(policy, principal, trigger_type, reason=active_reason)

        existing = self._existing_run(policy, drift_signal, alert_signal)
        if existing is not None:
            return RetrainingEvaluation(
                policy_id=policy.id,
                decision=RetrainingDecision.SKIPPED,
                triggered=False,
                reason="A retraining run already exists for this trigger.",
                run=existing,
            )

        accepted, trigger_reason = self._trigger_accepts_signal(policy, drift_signal, alert_signal)
        if not manual_override and not accepted:
            return self._skip(
                policy,
                principal,
                trigger_type,
                reason=trigger_reason,
                drift_signal=drift_signal,
                alert_signal=alert_signal,
            )

        guardrail_allowed, guardrail_reason = self._guardrails_allow_run(policy)
        if not guardrail_allowed:
            return self._skip(
                policy,
                principal,
                trigger_type,
                reason=guardrail_reason,
                drift_signal=drift_signal,
                alert_signal=alert_signal,
            )

        run_id = uuid4()
        training_config = self._build_training_config(
            policy,
            run_id,
            trigger_type,
            drift_signal,
            alert_signal,
        )
        pending = RetrainingRun(
            id=run_id,
            organization_id=policy.organization_id,
            project_id=policy.project_id,
            policy_id=policy.id,
            deployment_id=policy.deployment_id,
            trigger_type=trigger_type,
            drift_report_id=drift_signal.drift_report_id if drift_signal else None,
            alert_event_id=alert_signal.alert_event_id if alert_signal else None,
            training_run_id=None,
            status=RetrainingRunStatus.PENDING_APPROVAL,
            reason=reason,
            training_config=training_config,
            decision_metadata=self._decision_metadata(trigger_reason, drift_signal, alert_signal),
            requested_by=UUID(principal.user_id),
            approved_by=None,
            rejected_by=None,
        )
        saved = self._repository.add_run(pending)
        if policy.approval_required:
            return RetrainingEvaluation(
                policy_id=policy.id,
                decision=RetrainingDecision.PENDING_APPROVAL,
                triggered=True,
                reason="Retraining run is waiting for approval.",
                run=saved,
            )

        request = self._training_request_from_config(training_config, UUID(principal.user_id))
        launch = self._training_launcher.launch_training_run(request, principal)
        queued = replace(
            saved,
            training_run_id=launch.training_run_id,
            status=RetrainingRunStatus.QUEUED,
            decision_metadata={
                **saved.decision_metadata,
                "training_status": launch.status,
                "orchestrator_run_id": launch.orchestrator_run_id,
            },
        )
        updated = self._repository.update_run(queued)
        return RetrainingEvaluation(
            policy_id=policy.id,
            decision=RetrainingDecision.TRIGGERED,
            triggered=True,
            reason="Retraining run was queued.",
            run=updated,
        )

    def _skip(
        self,
        policy: RetrainingPolicy,
        principal: Principal,
        trigger_type: RetrainingTriggerType,
        *,
        reason: str,
        drift_signal: DriftRetrainingSignal | None = None,
        alert_signal: AlertRetrainingSignal | None = None,
    ) -> RetrainingEvaluation:
        run = RetrainingRun(
            id=uuid4(),
            organization_id=policy.organization_id,
            project_id=policy.project_id,
            policy_id=policy.id,
            deployment_id=policy.deployment_id,
            trigger_type=trigger_type,
            drift_report_id=drift_signal.drift_report_id if drift_signal else None,
            alert_event_id=alert_signal.alert_event_id if alert_signal else None,
            training_run_id=None,
            status=RetrainingRunStatus.SKIPPED,
            reason=reason,
            training_config=policy.training_template,
            decision_metadata=self._decision_metadata(reason, drift_signal, alert_signal),
            requested_by=UUID(principal.user_id),
            approved_by=None,
            rejected_by=None,
        )
        saved = self._repository.add_run(run)
        return RetrainingEvaluation(
            policy_id=policy.id,
            decision=RetrainingDecision.SKIPPED,
            triggered=False,
            reason=reason,
            run=saved,
        )

    def _load_policy_source(
        self,
        policy: RetrainingPolicy,
        command: EvaluateRetrainingPolicyCommand,
    ) -> tuple[DriftRetrainingSignal | None, AlertRetrainingSignal | None]:
        if policy.trigger_type == RetrainingTriggerType.DRIFT:
            if command.drift_report_id is None:
                raise DomainValidationError("Drift-triggered retraining requires a drift report.")
            signal = self._repository.get_drift_signal(command.drift_report_id)
            if signal is None or not _same_scope(policy, signal):
                raise ResourceNotFoundError("Drift report was not found.")
            if signal.deployment_id != policy.deployment_id:
                raise ResourceNotFoundError("Drift report was not found.")
            return signal, None
        if policy.trigger_type == RetrainingTriggerType.ALERT:
            if command.alert_event_id is None:
                raise DomainValidationError("Alert-triggered retraining requires an alert event.")
            signal = self._repository.get_alert_signal(command.alert_event_id)
            if signal is None or not _same_scope(policy, signal):
                raise ResourceNotFoundError("Alert event was not found.")
            if signal.deployment_id != policy.deployment_id:
                raise ResourceNotFoundError("Alert event was not found.")
            return None, signal
        return None, None

    def _trigger_accepts_signal(
        self,
        policy: RetrainingPolicy,
        drift_signal: DriftRetrainingSignal | None,
        alert_signal: AlertRetrainingSignal | None,
    ) -> tuple[bool, str]:
        if policy.trigger_type == RetrainingTriggerType.DRIFT:
            if drift_signal is None:
                return True, "Manual retraining override."
            return retraining_policy_accepts_drift(policy, drift_signal)
        if policy.trigger_type == RetrainingTriggerType.ALERT:
            if alert_signal is None:
                return True, "Manual retraining override."
            return retraining_policy_accepts_alert(policy, alert_signal)
        return True, "Manual retraining policy was triggered."

    def _guardrails_allow_run(self, policy: RetrainingPolicy) -> tuple[bool, str]:
        now = datetime.now(tz=UTC)
        latest_created_at = self._repository.latest_run_created_at(policy.id)
        if latest_created_at is not None:
            elapsed_seconds = (now - _ensure_aware(latest_created_at)).total_seconds()
            if elapsed_seconds < policy.cooldown_seconds:
                return False, "Retraining policy cooldown has not elapsed."
        since = now - timedelta(days=1)
        if self._repository.count_runs_since(policy.id, since) >= policy.max_runs_per_day:
            return False, "Retraining policy has reached its daily run limit."
        return True, "Retraining guardrails allow a new run."

    def _existing_run(
        self,
        policy: RetrainingPolicy,
        drift_signal: DriftRetrainingSignal | None,
        alert_signal: AlertRetrainingSignal | None,
    ) -> RetrainingRun | None:
        if drift_signal is None and alert_signal is None:
            return None
        return self._repository.get_existing_run_for_trigger(
            policy.id,
            drift_signal.drift_report_id if drift_signal else None,
            alert_signal.alert_event_id if alert_signal else None,
        )

    def _validate_training_references(
        self,
        command: CreateRetrainingPolicyCommand,
        training_template: dict[str, object],
    ) -> None:
        experiment_id = UUID(str(training_template["experiment_id"]))
        if not self._repository.experiment_belongs_to_project(
            command.organization_id,
            command.project_id,
            experiment_id,
        ):
            raise ResourceNotFoundError("Experiment was not found.")
        dataset_version_id = training_template.get("dataset_version_id")
        if dataset_version_id and not self._repository.dataset_version_belongs_to_project(
            command.project_id,
            UUID(str(dataset_version_id)),
        ):
            raise ResourceNotFoundError("Dataset version was not found.")
        feature_set_id = training_template.get("feature_set_id")
        if feature_set_id and not self._repository.feature_set_belongs_to_project(
            command.project_id,
            UUID(str(feature_set_id)),
        ):
            raise ResourceNotFoundError("Feature set was not found.")

    def _build_training_config(
        self,
        policy: RetrainingPolicy,
        run_id: UUID,
        trigger_type: RetrainingTriggerType,
        drift_signal: DriftRetrainingSignal | None,
        alert_signal: AlertRetrainingSignal | None,
    ) -> dict[str, object]:
        template = policy.training_template
        source_suffix = trigger_type.value
        run_name = f"{template['run_name_prefix']}-{source_suffix}-{run_id.hex[:8]}"
        return {
            **template,
            "organization_id": str(policy.organization_id),
            "project_id": str(policy.project_id),
            "run_name": run_name,
            "trigger_type": trigger_type.value,
            "policy_id": str(policy.id),
            "deployment_id": str(policy.deployment_id),
            "drift_report_id": str(drift_signal.drift_report_id) if drift_signal else None,
            "alert_event_id": str(alert_signal.alert_event_id) if alert_signal else None,
        }

    def _training_request_from_config(
        self,
        training_config: dict[str, object],
        requested_by: UUID,
    ) -> RetrainingTrainingRequest:
        return RetrainingTrainingRequest(
            organization_id=UUID(str(training_config["organization_id"])),
            project_id=UUID(str(training_config["project_id"])),
            experiment_id=UUID(str(training_config["experiment_id"])),
            run_name=str(training_config["run_name"]),
            dataset_version_id=(
                UUID(str(training_config["dataset_version_id"]))
                if training_config.get("dataset_version_id")
                else None
            ),
            feature_set_id=(
                UUID(str(training_config["feature_set_id"]))
                if training_config.get("feature_set_id")
                else None
            ),
            algorithm=str(training_config["algorithm"]),
            model_type=str(training_config["model_type"]),
            objective_metric_name=str(training_config["objective_metric_name"]),
            hyperparameters=dict(training_config.get("hyperparameters", {})),
            requested_by=requested_by,
        )

    def _decision_metadata(
        self,
        reason: str,
        drift_signal: DriftRetrainingSignal | None,
        alert_signal: AlertRetrainingSignal | None,
    ) -> dict[str, object]:
        metadata: dict[str, object] = {"reason": reason}
        if drift_signal is not None:
            metadata.update(
                {
                    "drift_score": drift_signal.drift_score,
                    "drifted_feature_count": drift_signal.drifted_feature_count,
                    "evaluated_feature_count": drift_signal.evaluated_feature_count,
                }
            )
        if alert_signal is not None:
            metadata.update(
                {
                    "alert_severity": alert_signal.severity,
                    "alert_observed_value": alert_signal.observed_value,
                    "alert_threshold": alert_signal.threshold,
                }
            )
        return metadata

    def _get_scoped_policy(self, policy_id: UUID, principal: Principal) -> RetrainingPolicy:
        policy = self._repository.get_policy(policy_id)
        if policy is None or str(policy.organization_id) != principal.organization_id:
            raise ResourceNotFoundError("Retraining policy was not found.")
        return policy

    def _get_scoped_run(self, run_id: UUID, principal: Principal) -> RetrainingRun:
        run = self._repository.get_run(run_id)
        if run is None or str(run.organization_id) != principal.organization_id:
            raise ResourceNotFoundError("Retraining run was not found.")
        return run

    def _require(self, principal: Principal, permission: str) -> None:
        if not principal.has(permission):
            raise PermissionDeniedError("You do not have permission to manage retraining.")

    def _require_same_organization(self, organization_id: UUID, principal: Principal) -> None:
        if str(organization_id) != principal.organization_id:
            raise PermissionDeniedError("You cannot manage retraining in another organization.")


def _same_scope(
    policy: RetrainingPolicy,
    signal: DriftRetrainingSignal | AlertRetrainingSignal,
) -> bool:
    return (
        signal.organization_id == policy.organization_id
        and signal.project_id == policy.project_id
    )


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
