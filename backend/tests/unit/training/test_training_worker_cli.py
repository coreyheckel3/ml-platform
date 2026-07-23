from uuid import uuid4

from scripts.workers.run_training_worker import summary_payload, worker_principal

from forgeml.modules.training.application.services import TrainingWorkerRunSummary


def test_training_worker_summary_payload_serializes_run_ids() -> None:
    training_run_id = uuid4()
    summary = TrainingWorkerRunSummary(
        worker_id="worker-a",
        scanned=3,
        executed=1,
        succeeded=1,
        failed=0,
        skipped=2,
        training_run_ids=[training_run_id],
    )

    payload = summary_payload(summary)

    assert payload == {
        "worker_id": "worker-a",
        "scanned": 3,
        "executed": 1,
        "succeeded": 1,
        "failed": 0,
        "skipped": 2,
        "training_run_ids": [str(training_run_id)],
    }


def test_training_worker_principal_is_scoped_to_organization() -> None:
    organization_id = uuid4()

    principal = worker_principal(organization_id)

    assert principal.organization_id == str(organization_id)
    assert principal.has("training_runs:write")
