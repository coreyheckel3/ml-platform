from uuid import uuid4

from forgeml.platform.serving import (
    SERVING_RUNTIME_SCHEMA_VERSION,
    InMemoryServingRuntimeGateway,
    ServingDeploymentRequest,
    ServingHealthProbeRequest,
    ServingRollbackRequest,
    ServingTrafficAllocation,
    build_serving_traffic_plan,
)


def test_in_memory_serving_runtime_deploys_routes_rolls_back_and_probes() -> None:
    gateway = InMemoryServingRuntimeGateway(base_url="http://serving.local")
    deployment_id = uuid4()
    revision_id = uuid4()
    previous_revision_id = uuid4()
    request = ServingDeploymentRequest(
        deployment_id=deployment_id,
        deployment_revision_id=revision_id,
        model_version_id=uuid4(),
        serving_image="ghcr.io/forgeml/serving/xgboost:1.0.0",
        runtime_config={},
        traffic_percentage=10,
    )

    deployed = gateway.deploy_revision(request)
    traffic = gateway.apply_traffic_plan(
        build_serving_traffic_plan(
            deployment_id=deployment_id,
            allocations=[
                ServingTrafficAllocation(revision_id, 25),
                ServingTrafficAllocation(previous_revision_id, 75),
            ],
        )
    )
    rollback = gateway.rollback(
        ServingRollbackRequest(
            deployment_id=deployment_id,
            target_revision_id=revision_id,
            previous_revision_ids=(previous_revision_id,),
        )
    )
    probe = gateway.probe_revision(
        ServingHealthProbeRequest(
            deployment_id=deployment_id,
            deployment_revision_id=revision_id,
            runtime_deployment_id=deployed.runtime_deployment_id,
            runtime_config={},
        )
    )

    assert deployed.runtime_deployment_id.startswith("local-serving://")
    assert deployed.metadata["schema_version"] == SERVING_RUNTIME_SCHEMA_VERSION
    assert traffic.metadata["total_traffic_percentage"] == 100
    assert rollback.previous_revision_ids == (previous_revision_id,)
    assert probe.status == "healthy"
    assert probe.error_rate < 0.01
    assert gateway.deployment_requests == [request]
    assert len(gateway.traffic_plan_requests) == 2
    assert gateway.rollback_requests[0].target_revision_id == revision_id
