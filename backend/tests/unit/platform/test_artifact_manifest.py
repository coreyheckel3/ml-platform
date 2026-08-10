import json
from uuid import uuid4

import pytest

from forgeml.platform.artifacts import (
    ARTIFACT_MANIFEST_SCHEMA_VERSION,
    ArtifactManifestStore,
    InMemoryArtifactStorageGateway,
    build_dataset_artifact_manifest,
    build_model_artifact_manifest,
    dataset_artifact_manifest_key,
    serialize_artifact_manifest,
    sha256_uri,
    validate_payload_checksum,
)
from forgeml.platform.domain.errors import DomainValidationError


def test_dataset_artifact_manifest_serializes_checksum_and_lineage() -> None:
    organization_id = uuid4()
    project_id = uuid4()
    dataset_id = uuid4()
    version_id = uuid4()
    user_id = uuid4()

    manifest = build_dataset_artifact_manifest(
        organization_id=organization_id,
        project_id=project_id,
        dataset_id=dataset_id,
        dataset_version_id=version_id,
        object_uri="s3://forgeml/datasets/transactions.csv",
        content_hash="sha256:abc123",
        size_bytes=128,
        row_count=2,
        schema_hash="schema-hash",
        created_by=user_id,
    )

    payload = json.loads(serialize_artifact_manifest(manifest))

    assert payload["schema_version"] == ARTIFACT_MANIFEST_SCHEMA_VERSION
    assert payload["artifact_set_type"] == "dataset_version"
    assert payload["artifacts"][0]["checksum_sha256"] == "sha256:abc123"
    assert {item["source_type"] for item in payload["lineage"]} == {
        "dataset",
        "dataset_version",
        "organization",
        "project",
        "user",
    }


def test_model_artifact_manifest_uses_training_execution_content_checksums() -> None:
    model_version_id = uuid4()
    artifact_payload = b'{"model":"xgb"}'

    manifest = build_model_artifact_manifest(
        organization_id=uuid4(),
        project_id=uuid4(),
        registered_model_id=uuid4(),
        model_version_id=model_version_id,
        training_run_id=uuid4(),
        experiment_run_id=uuid4(),
        dataset_version_id=uuid4(),
        feature_set_id=uuid4(),
        artifact_uri="s3://forgeml/training-runs/run-1/model.json",
        model_format="xgboost-booster",
        signature={"inputs": [], "outputs": []},
        metrics={"auc": 0.94},
        created_by=uuid4(),
        training_execution={
            "schema_version": "forgeml.training_execution_result.v1",
            "artifacts": [
                {
                    "name": "model",
                    "artifact_type": "model",
                    "uri": "file:///tmp/model.json",
                    "media_type": "application/json",
                    "metadata": {
                        "control_plane_uri": "s3://forgeml/training-runs/run-1/model.json",
                        "size_bytes": len(artifact_payload),
                        "sha256": sha256_uri(artifact_payload),
                    },
                }
            ],
        },
    )

    payload = json.loads(serialize_artifact_manifest(manifest))
    artifact = payload["artifacts"][0]

    assert artifact["uri"] == "s3://forgeml/training-runs/run-1/model.json"
    assert artifact["checksum_sha256"] == sha256_uri(artifact_payload)
    assert artifact["metadata"]["checksum_source"] == "artifact_content"


def test_manifest_store_writes_deterministic_payload_with_verified_checksum() -> None:
    gateway = InMemoryArtifactStorageGateway(bucket="forgeml-artifacts")
    store = ArtifactManifestStore(gateway)
    organization_id = uuid4()
    project_id = uuid4()
    dataset_id = uuid4()
    version_id = uuid4()
    key = dataset_artifact_manifest_key(
        organization_id=organization_id,
        project_id=project_id,
        dataset_id=dataset_id,
        dataset_version_id=version_id,
    )
    manifest = build_dataset_artifact_manifest(
        organization_id=organization_id,
        project_id=project_id,
        dataset_id=dataset_id,
        dataset_version_id=version_id,
        object_uri="s3://forgeml/datasets/transactions.csv",
        content_hash="sha256:def456",
        size_bytes=256,
        row_count=3,
        schema_hash="schema-hash",
        created_by=uuid4(),
    )

    stored = store.put_manifest(key=key, manifest=manifest)

    assert gateway.exists(key=key)
    assert stored.uri == f"s3://forgeml-artifacts/{key}"
    assert stored.checksum_sha256 == sha256_uri(gateway.get_bytes(key=key))


def test_payload_checksum_validation_rejects_tampering() -> None:
    checksum = sha256_uri(b"trusted-payload")

    with pytest.raises(DomainValidationError):
        validate_payload_checksum(b"tampered-payload", checksum)
