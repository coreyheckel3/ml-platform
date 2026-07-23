from __future__ import annotations

import argparse
import json
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from forgeml.modules.training.application.services import (
    ExecuteNextTrainingRunsCommand,
    TrainingRunService,
    TrainingWorkerRunSummary,
)
from forgeml.modules.training.infrastructure.execution import LocalExampleTrainingRunner
from forgeml.modules.training.infrastructure.orchestrator import LocalTrainingWorkflowOrchestrator
from forgeml.modules.training.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyExperimentRunRecorder,
    SqlAlchemyTrainingRunRepository,
)
from forgeml.platform.config import get_settings
from forgeml.platform.security.rbac import Principal


def run_once(
    *,
    organization_id: UUID,
    project_id: UUID | None = None,
    max_runs: int = 1,
    worker_id: str = "local-training-worker",
) -> TrainingWorkerRunSummary:
    settings = get_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
    with Session(engine) as session:
        service = TrainingRunService(
            training_runs=SqlAlchemyTrainingRunRepository(session),
            experiment_runs=SqlAlchemyExperimentRunRecorder(session),
            orchestrator=LocalTrainingWorkflowOrchestrator(),
            artifact_bucket=settings.object_storage_bucket,
            runner=LocalExampleTrainingRunner(settings.local_training_artifact_root),
        )
        summary = service.execute_next_training_runs(
            ExecuteNextTrainingRunsCommand(
                organization_id=organization_id,
                project_id=project_id,
                max_runs=max_runs,
                worker_id=worker_id,
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
        "training_run_ids": [str(training_run_id) for training_run_id in summary.training_run_ids],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one ForgeML training worker polling cycle.")
    parser.add_argument("--organization-id", required=True, type=UUID)
    parser.add_argument("--project-id", type=UUID)
    parser.add_argument("--max-runs", type=int, default=1)
    parser.add_argument("--worker-id", default="local-training-worker")
    args = parser.parse_args()

    summary = run_once(
        organization_id=args.organization_id,
        project_id=args.project_id,
        max_runs=args.max_runs,
        worker_id=args.worker_id,
    )
    print(json.dumps(summary_payload(summary), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
