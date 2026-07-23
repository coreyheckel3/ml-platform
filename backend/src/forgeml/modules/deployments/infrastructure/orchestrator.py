from forgeml.modules.deployments.domain.entities import Deployment, DeploymentRevision


class LocalDeploymentOrchestrator:
    def deploy_revision(self, deployment: Deployment, revision: DeploymentRevision) -> str:
        return f"local-serving:{deployment.project_id}:{deployment.id}:{revision.id}"

    def update_traffic(self, deployment: Deployment, revision: DeploymentRevision) -> str:
        return f"local-serving-traffic:{deployment.id}:{revision.id}:{revision.traffic_percentage}"

    def rollback(
        self,
        deployment: Deployment,
        target_revision: DeploymentRevision,
        previous_revision: DeploymentRevision | None,
    ) -> str:
        previous_id = str(previous_revision.id) if previous_revision else "none"
        return f"local-serving-rollback:{deployment.id}:{previous_id}:{target_revision.id}"
