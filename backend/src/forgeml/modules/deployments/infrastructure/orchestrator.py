from forgeml.modules.deployments.domain.entities import Deployment, DeploymentRevision
from forgeml.platform.serving import (
    InMemoryServingRuntimeGateway,
    ServingDeploymentRequest,
    ServingHealthProbeRequest,
    ServingHealthProbeResult,
    ServingRollbackRequest,
    ServingRuntimeGateway,
    ServingTrafficAllocation,
    build_serving_traffic_plan,
)


class LocalDeploymentOrchestrator:
    def __init__(self, gateway: ServingRuntimeGateway | None = None) -> None:
        self._gateway = gateway or InMemoryServingRuntimeGateway()

    def deploy_revision(self, deployment: Deployment, revision: DeploymentRevision) -> str:
        record = self._gateway.deploy_revision(
            ServingDeploymentRequest(
                deployment_id=deployment.id,
                deployment_revision_id=revision.id,
                model_version_id=revision.model_version_id,
                serving_image=revision.serving_image,
                runtime_config=revision.runtime_config,
                traffic_percentage=revision.traffic_percentage,
            )
        )
        return record.runtime_deployment_id

    def update_traffic(self, deployment: Deployment, revision: DeploymentRevision) -> str:
        result = self._gateway.apply_traffic_plan(
            build_serving_traffic_plan(
                deployment_id=deployment.id,
                allocations=[
                    ServingTrafficAllocation(
                        deployment_revision_id=revision.id,
                        traffic_percentage=revision.traffic_percentage,
                    )
                ],
            )
        )
        return (
            f"local-serving-traffic:{result.deployment_id}:"
            f"{revision.id}:{revision.traffic_percentage}"
        )

    def rollback(
        self,
        deployment: Deployment,
        target_revision: DeploymentRevision,
        previous_revision: DeploymentRevision | None,
    ) -> str:
        previous_revision_ids = () if previous_revision is None else (previous_revision.id,)
        result = self._gateway.rollback(
            ServingRollbackRequest(
                deployment_id=deployment.id,
                target_revision_id=target_revision.id,
                previous_revision_ids=previous_revision_ids,
            )
        )
        previous_id = str(previous_revision.id) if previous_revision else "none"
        return f"local-serving-rollback:{result.deployment_id}:{previous_id}:{target_revision.id}"

    def probe_revision(
        self,
        deployment: Deployment,
        revision: DeploymentRevision,
    ) -> ServingHealthProbeResult:
        return self._gateway.probe_revision(
            ServingHealthProbeRequest(
                deployment_id=deployment.id,
                deployment_revision_id=revision.id,
                runtime_deployment_id=revision.orchestrator_deployment_id,
                runtime_config=revision.runtime_config,
            )
        )
