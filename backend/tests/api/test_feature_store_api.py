from dataclasses import dataclass
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from forgeml.main import create_app
from forgeml.modules.feature_store.api.routes import get_feature_store_service
from forgeml.modules.feature_store.domain.entities import (
    FeatureDefinition,
    FeatureLineage,
    FeatureMaterialization,
    FeatureMaterializationStatus,
    FeaturePipeline,
    FeaturePipelineStatus,
    FeatureSet,
    FeatureSetStatus,
)
from forgeml.platform.api.dependencies import get_current_principal
from forgeml.platform.security.rbac import Principal


@dataclass
class FakeFeatureStoreService:
    organization_id: UUID
    project_id: UUID
    feature_set_id: UUID
    pipeline_id: UUID
    materialization_id: UUID
    source_dataset_id: UUID

    def create_feature_set(self, command, principal):
        assert command.name == "Merchant Signals"
        return self._feature_set()

    def list_feature_sets(self, project_id, principal):
        assert project_id == self.project_id
        return [self._feature_set()]

    def get_feature_set(self, feature_set_id, principal):
        assert feature_set_id == self.feature_set_id
        return self._feature_set()

    def register_feature_definitions(self, command, principal):
        assert command.definitions[0].name == "chargeback_rate_30d"
        return [self._definition()]

    def list_feature_definitions(self, feature_set_id, principal):
        assert feature_set_id == self.feature_set_id
        return [self._definition()]

    def register_pipeline(self, command, principal):
        assert command.name == "daily materialization"
        return self._pipeline()

    def list_pipelines(self, feature_set_id, principal):
        assert feature_set_id == self.feature_set_id
        return [self._pipeline()]

    def materialize_pipeline(self, command, principal):
        assert command.pipeline_id == self.pipeline_id
        return self._materialization()

    def list_materializations(self, feature_set_id, principal):
        assert feature_set_id == self.feature_set_id
        return [self._materialization()]

    def get_lineage(self, feature_set_id, principal):
        assert feature_set_id == self.feature_set_id
        return [self._lineage()]

    def _feature_set(self) -> FeatureSet:
        return FeatureSet(
            id=self.feature_set_id,
            organization_id=self.organization_id,
            project_id=self.project_id,
            name="Merchant Signals",
            slug="merchant-signals",
            description="Merchant behavior features.",
            entity_key="merchant_id",
            status=FeatureSetStatus.ACTIVE,
        )

    def _definition(self) -> FeatureDefinition:
        return FeatureDefinition(
            id=uuid4(),
            feature_set_id=self.feature_set_id,
            name="chargeback_rate_30d",
            dtype="float",
            description="Rolling chargeback rate.",
            nullable=False,
            constraints={"min": 0, "max": 1},
        )

    def _pipeline(self) -> FeaturePipeline:
        return FeaturePipeline(
            id=self.pipeline_id,
            feature_set_id=self.feature_set_id,
            name="daily materialization",
            source_dataset_id=self.source_dataset_id,
            code_ref="git://feature-pipelines/merchant_signals.py",
            schedule_cron="0 3 * * *",
            status=FeaturePipelineStatus.ACTIVE,
        )

    def _materialization(self) -> FeatureMaterialization:
        return FeatureMaterialization(
            id=self.materialization_id,
            feature_set_id=self.feature_set_id,
            pipeline_id=self.pipeline_id,
            version=1,
            offline_uri="s3://forgeml/features/materialization",
            online_ref="feature-set:merchant:v1",
            orchestrator_run_id="run-1",
            status=FeatureMaterializationStatus.REQUESTED,
        )

    def _lineage(self) -> FeatureLineage:
        return FeatureLineage(
            id=uuid4(),
            feature_set_id=self.feature_set_id,
            upstream_type="dataset",
            upstream_id=str(self.source_dataset_id),
        )


def test_feature_store_routes_expose_metadata_and_materialization_lifecycle() -> None:
    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    service = FakeFeatureStoreService(
        organization_id=organization_id,
        project_id=project_id,
        feature_set_id=uuid4(),
        pipeline_id=uuid4(),
        materialization_id=uuid4(),
        source_dataset_id=uuid4(),
    )
    app = create_app()
    app.dependency_overrides[get_feature_store_service] = lambda: service
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        user_id=str(user_id),
        email="owner@example.com",
        organization_id=str(organization_id),
        permissions=frozenset({"*"}),
    )
    client = TestClient(app)

    created = client.post(
        f"/api/v1/projects/{project_id}/feature-sets",
        json={
            "name": "Merchant Signals",
            "description": "Merchant behavior features.",
            "entity_key": "merchant_id",
        },
    )
    listed = client.get(f"/api/v1/projects/{project_id}/feature-sets")
    definitions = client.post(
        f"/api/v1/feature-sets/{service.feature_set_id}/features",
        json={
            "definitions": [
                {
                    "name": "chargeback_rate_30d",
                    "dtype": "float",
                    "description": "Rolling chargeback rate.",
                    "nullable": False,
                    "constraints": {"min": 0, "max": 1},
                }
            ]
        },
    )
    pipeline = client.post(
        f"/api/v1/feature-sets/{service.feature_set_id}/pipelines",
        json={
            "name": "daily materialization",
            "source_dataset_id": str(service.source_dataset_id),
            "code_ref": "git://feature-pipelines/merchant_signals.py",
            "schedule_cron": "0 3 * * *",
        },
    )
    materialization = client.post(f"/api/v1/feature-pipelines/{service.pipeline_id}/materialize")
    lineage = client.get(f"/api/v1/feature-sets/{service.feature_set_id}/lineage")

    assert created.status_code == 201
    assert created.json()["slug"] == "merchant-signals"
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == str(service.feature_set_id)
    assert definitions.status_code == 200
    assert definitions.json()["items"][0]["dtype"] == "float"
    assert pipeline.status_code == 201
    assert pipeline.json()["source_dataset_id"] == str(service.source_dataset_id)
    assert materialization.status_code == 202
    assert materialization.json()["status"] == "requested"
    assert lineage.status_code == 200
    assert lineage.json()["items"][0]["upstream_type"] == "dataset"

