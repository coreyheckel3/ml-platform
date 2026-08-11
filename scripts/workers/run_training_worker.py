from __future__ import annotations

import argparse
import json
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from forgeml.modules.training.application.services import (
    ExecuteNextTrainingRunsCommand,
    TrainingRetryPolicy,
    TrainingRunService,
    TrainingWorkerRunSummary,
)
from forgeml.modules.training.infrastructure.execution import LocalExampleTrainingRunner
from forgeml.modules.training.infrastructure.orchestrator import (
    build_training_workflow_orchestrator,
)
from forgeml.modules.training.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyExperimentRunRecorder,
    SqlAlchemyTrainingRunRepository,
)
from forgeml.platform.config import get_settings
from forgeml.platform.mlflow import build_mlflow_tracking_gateway
from forgeml.platform.security.rbac import Principal


def run_once(
    *,
    organization_id: UUID,
    project_id: UUID | None = None,
    max_runs: int = 1,
    worker_id: str = "local-training-worker",
    retry_policy: TrainingRetryPolicy | None = None,
    recover_expired_leases: bool = True,
) -> TrainingWorkerRunSummary:
    settings = get_settings()
    resolved_retry_policy = retry_policy or TrainingRetryPolicy(
        max_attempts=settings.training_worker_max_attempts,
        base_backoff_seconds=settings.training_worker_retry_backoff_seconds,
        max_backoff_seconds=settings.training_worker_max_retry_backoff_seconds,
        lease_seconds=settings.training_worker_lease_seconds,
    )
    engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
    with Session(engine) as session:
        service = TrainingRunService(
            training_runs=SqlAlchemyTrainingRunRepository(session),
            experiment_runs=SqlAlchemyExperimentRunRecorder(session),
            orchestrator=build_training_workflow_orchestrator(settings),
            artifact_bucket=settings.object_storage_bucket,
            runner=LocalExampleTrainingRunner(settings.local_training_artifact_root),
            retry_policy=resolved_retry_policy,
            mlflow_tracking=build_mlflow_tracking_gateway(
                enabled=settings.mlflow_sync_enabled,
                tracking_uri=settings.mlflow_tracking_uri,
                timeout_seconds=settings.mlflow_http_timeout_seconds,
            ),
            mlflow_experiment_prefix=settings.mlflow_experiment_prefix,
        )
        summary = service.execute_next_training_runs(
            ExecuteNextTrainingRunsCommand(
                organization_id=organization_id,
                project_id=project_id,
                max_runs=max_runs,
                worker_id=worker_id,
                recover_expired_leases=recover_expired_leases,
            ),
            worker_principal(organization_id),
        )
        session.commit()
        return summary


def worker_principal(organization_id: UUID) -> Principal:
    return Principal(
        user_id="00000000-0000-0000-0000-000000000000",
        email="training-worker@forgeml.internal",
        organization_id=str(organization_id),
        permissions=frozenset({"training_runs:write"}),
    )


def summary_payload(summary: TrainingWorkerRunSummary) -> dict[str, object]:
    return {
        "worker_id": summary.worker_id,
        "scanned": summary.scanned,
        "executed": summary.executed,
        "succeeded": summary.succeeded,
        "failed": summary.failed,
        "skipped": summary.skipped,
        "retried": summary.retried,
        "dead_lettered": summary.dead_lettered,
        "expired_leases_requeued": summary.expired_leases_requeued,
        "expired_leases_dead_lettered": summary.expired_leases_dead_lettered,
        "heartbeats": summary.heartbeats,
        "training_run_ids": [str(training_run_id) for training_run_id in summary.training_run_ids],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one ForgeML training worker polling cycle.")
    parser.add_argument("--organization-id", required=True, type=UUID)
    parser.add_argument("--project-id", type=UUID)
    parser.add_argument("--max-runs", type=int, default=1)
    parser.add_argument("--worker-id", default="local-training-worker")
    parser.add_argument("--max-attempts", type=int)
    parser.add_argument("--lease-seconds", type=int)
    parser.add_argument("--retry-backoff-seconds", type=int)
    parser.add_argument("--max-retry-backoff-seconds", type=int)
    parser.add_argument(
        "--skip-expired-lease-recovery",
        action="store_true",
        help="Skip stale running-run lease recovery before polling queued work.",
    )
    args = parser.parse_args()
    settings = get_settings()
    retry_policy = TrainingRetryPolicy(
        max_attempts=args.max_attempts or settings.training_worker_max_attempts,
        base_backoff_seconds=(
            args.retry_backoff_seconds
            if args.retry_backoff_seconds is not None
            else settings.training_worker_retry_backoff_seconds
        ),
        max_backoff_seconds=(
            args.max_retry_backoff_seconds
            if args.max_retry_backoff_seconds is not None
            else settings.training_worker_max_retry_backoff_seconds
        ),
        lease_seconds=args.lease_seconds or settings.training_worker_lease_seconds,
    )

    summary = run_once(
        organization_id=args.organization_id,
        project_id=args.project_id,
        max_runs=args.max_runs,
        worker_id=args.worker_id,
        retry_policy=retry_policy,
        recover_expired_leases=not args.skip_expired_lease_recovery,
    )
    print(json.dumps(summary_payload(summary), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
