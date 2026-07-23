from forgeml.modules.retraining.domain.entities import (
    RetrainingTrainingLaunch,
    RetrainingTrainingRequest,
)
from forgeml.modules.training.application.services import (
    StartTrainingRunCommand,
    TrainingRunService,
)
from forgeml.platform.security.rbac import Principal


class TrainingRunServiceLauncher:
    def __init__(self, training_service: TrainingRunService) -> None:
        self._training_service = training_service

    def launch_training_run(
        self,
        request: RetrainingTrainingRequest,
        principal: Principal,
    ) -> RetrainingTrainingLaunch:
        training_principal = Principal(
            user_id=principal.user_id,
            email=principal.email,
            organization_id=principal.organization_id,
            permissions=frozenset({*principal.permissions, "training_runs:create"}),
        )
        training_run = self._training_service.start_training_run(
            StartTrainingRunCommand(
                organization_id=request.organization_id,
                project_id=request.project_id,
                experiment_id=request.experiment_id,
                run_name=request.run_name,
                dataset_version_id=request.dataset_version_id,
                feature_set_id=request.feature_set_id,
                algorithm=request.algorithm,
                model_type=request.model_type,
                objective_metric_name=request.objective_metric_name,
                hyperparameters=request.hyperparameters,
                requested_by=request.requested_by,
            ),
            training_principal,
        )
        return RetrainingTrainingLaunch(
            training_run_id=training_run.id,
            status=training_run.status.value,
            orchestrator_run_id=training_run.orchestrator_run_id,
        )
