from forgeml.modules.training.domain.entities import TrainingRun


class LocalTrainingWorkflowOrchestrator:
    def trigger_training(self, training_run: TrainingRun) -> str:
        return f"local-training:{training_run.project_id}:{training_run.id}"

    def cancel_training(self, training_run: TrainingRun) -> str:
        return f"local-training-cancel:{training_run.orchestrator_run_id}"
