from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from forgeml.platform.domain.errors import DomainValidationError

ARTIFACT_MANIFEST_SCHEMA_VERSION = "forgeml.artifact_manifest.v1"


@dataclass(frozen=True)
class ArtifactDescriptor:
    name: str
    artifact_type: str
    uri: str
    media_type: str
    size_bytes: int
    checksum_sha256: str
    metadata: dict[str, object]


@dataclass(frozen=True)
class ArtifactLineageReference:
    source_type: str
    source_id: str
    relation: str


@dataclass(frozen=True)
class ArtifactManifest:
    artifact_set_type: str
    artifact_set_id: str
    artifact_root_uri: str
    producer: str
    artifacts: tuple[ArtifactDescriptor, ...]
    lineage: tuple[ArtifactLineageReference, ...]
    metadata: dict[str, object]
    created_at: datetime
    schema_version: str = ARTIFACT_MANIFEST_SCHEMA_VERSION


def build_dataset_artifact_manifest(
    *,
    organization_id: UUID,
    project_id: UUID,
    dataset_id: UUID,
    dataset_version_id: UUID,
    object_uri: str,
    content_hash: str,
    size_bytes: int,
    row_count: int,
    schema_hash: str,
    created_by: UUID,
) -> ArtifactManifest:
    descriptor = ArtifactDescriptor(
        name="dataset",
        artifact_type="dataset",
        uri=object_uri,
        media_type="application/octet-stream",
        size_bytes=size_bytes,
        checksum_sha256=normalize_sha256(content_hash),
        metadata={
            "checksum_source": "dataset_version.content_hash",
            "row_count": row_count,
            "schema_hash": schema_hash,
        },
    )
    return ArtifactManifest(
        artifact_set_type="dataset_version",
        artifact_set_id=str(dataset_version_id),
        artifact_root_uri=object_uri,
        producer="forgeml.datasets",
        artifacts=(descriptor,),
        lineage=(
            ArtifactLineageReference("organization", str(organization_id), "owned_by"),
            ArtifactLineageReference("project", str(project_id), "belongs_to"),
            ArtifactLineageReference("dataset", str(dataset_id), "versions"),
            ArtifactLineageReference("dataset_version", str(dataset_version_id), "describes"),
            ArtifactLineageReference("user", str(created_by), "created_by"),
        ),
        metadata={
            "row_count": row_count,
            "schema_hash": schema_hash,
            "immutability": "dataset_version",
        },
        created_at=_utcnow(),
    )


def build_model_artifact_manifest(
    *,
    organization_id: UUID,
    project_id: UUID,
    registered_model_id: UUID,
    model_version_id: UUID,
    training_run_id: UUID,
    experiment_run_id: UUID,
    artifact_uri: str,
    model_format: str,
    signature: dict[str, object],
    metrics: dict[str, float],
    created_by: UUID,
    dataset_version_id: UUID | None = None,
    feature_set_id: UUID | None = None,
    training_execution: dict[str, object] | None = None,
) -> ArtifactManifest:
    artifacts = _training_execution_artifacts(
        training_execution,
        fallback_name="model",
        fallback_type="model",
        fallback_uri=artifact_uri,
        fallback_media_type=_model_media_type(model_format),
    )
    lineage = [
        ArtifactLineageReference("organization", str(organization_id), "owned_by"),
        ArtifactLineageReference("project", str(project_id), "belongs_to"),
        ArtifactLineageReference("registered_model", str(registered_model_id), "versions"),
        ArtifactLineageReference("model_version", str(model_version_id), "describes"),
        ArtifactLineageReference("training_run", str(training_run_id), "trained_from"),
        ArtifactLineageReference("experiment_run", str(experiment_run_id), "evaluated_by"),
        ArtifactLineageReference("user", str(created_by), "created_by"),
    ]
    if dataset_version_id is not None:
        lineage.append(
            ArtifactLineageReference(
                "dataset_version",
                str(dataset_version_id),
                "trained_on",
            )
        )
    if feature_set_id is not None:
        lineage.append(
            ArtifactLineageReference("feature_set", str(feature_set_id), "uses_features")
        )

    return ArtifactManifest(
        artifact_set_type="model_version",
        artifact_set_id=str(model_version_id),
        artifact_root_uri=artifact_uri,
        producer="forgeml.model_registry",
        artifacts=artifacts,
        lineage=tuple(lineage),
        metadata={
            "model_format": model_format,
            "signature": signature,
            "metrics": metrics,
            "training_execution_schema_version": (
                training_execution.get("schema_version")
                if isinstance(training_execution, dict)
                else None
            ),
        },
        created_at=_utcnow(),
    )


def dataset_artifact_manifest_key(
    *,
    organization_id: UUID,
    project_id: UUID,
    dataset_id: UUID,
    dataset_version_id: UUID,
) -> str:
    return (
        f"organizations/{organization_id}/projects/{project_id}/datasets/{dataset_id}/"
        f"versions/{dataset_version_id}/artifact-manifest.json"
    )


def model_artifact_manifest_key(
    *,
    organization_id: UUID,
    project_id: UUID,
    registered_model_id: UUID,
    model_version_id: UUID,
) -> str:
    return (
        f"organizations/{organization_id}/projects/{project_id}/models/{registered_model_id}/"
        f"versions/{model_version_id}/artifact-manifest.json"
    )


def validate_artifact_manifest(manifest: ArtifactManifest) -> None:
    if manifest.schema_version != ARTIFACT_MANIFEST_SCHEMA_VERSION:
        raise DomainValidationError("Artifact manifest schema version is not supported.")
    if not manifest.artifact_set_type.strip():
        raise DomainValidationError("Artifact manifest artifact set type is required.")
    if not manifest.artifact_set_id.strip():
        raise DomainValidationError("Artifact manifest artifact set ID is required.")
    if len(manifest.artifacts) == 0:
        raise DomainValidationError("Artifact manifest must include at least one artifact.")
    names = [artifact.name for artifact in manifest.artifacts]
    if len(set(names)) != len(names):
        raise DomainValidationError("Artifact manifest artifact names must be unique.")
    for artifact in manifest.artifacts:
        _validate_artifact_descriptor(artifact)
    for reference in manifest.lineage:
        _validate_lineage_reference(reference)


def validate_payload_checksum(payload: bytes, expected_sha256: str) -> None:
    expected = normalize_sha256(expected_sha256)
    actual = sha256_uri(payload)
    if actual != expected:
        raise DomainValidationError("Artifact payload checksum does not match manifest metadata.")


def serialize_artifact_manifest(manifest: ArtifactManifest) -> bytes:
    validate_artifact_manifest(manifest)
    return json.dumps(
        _manifest_to_payload(manifest),
        indent=2,
        sort_keys=True,
    ).encode("utf-8") + b"\n"


def sha256_hexdigest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_uri(payload: bytes) -> str:
    return f"sha256:{sha256_hexdigest(payload)}"


def normalize_sha256(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise DomainValidationError("Artifact checksum is required.")
    if stripped.startswith("sha256:"):
        digest = stripped.removeprefix("sha256:")
    else:
        digest = stripped
    if not digest.strip():
        raise DomainValidationError("Artifact checksum digest is required.")
    return f"sha256:{digest.strip().lower()}"


def _training_execution_artifacts(
    training_execution: dict[str, object] | None,
    *,
    fallback_name: str,
    fallback_type: str,
    fallback_uri: str,
    fallback_media_type: str,
) -> tuple[ArtifactDescriptor, ...]:
    if not isinstance(training_execution, dict):
        return (
            _reference_artifact_descriptor(
                name=fallback_name,
                artifact_type=fallback_type,
                uri=fallback_uri,
                media_type=fallback_media_type,
            ),
        )

    raw_artifacts = training_execution.get("artifacts")
    if not isinstance(raw_artifacts, list) or not raw_artifacts:
        return (
            _reference_artifact_descriptor(
                name=fallback_name,
                artifact_type=fallback_type,
                uri=fallback_uri,
                media_type=fallback_media_type,
            ),
        )

    descriptors = []
    for index, raw_artifact in enumerate(raw_artifacts):
        if not isinstance(raw_artifact, dict):
            continue
        name = str(raw_artifact.get("name") or f"artifact-{index + 1}")
        artifact_type = str(raw_artifact.get("artifact_type") or "artifact")
        metadata = _metadata(raw_artifact.get("metadata"))
        uri = _artifact_uri(raw_artifact, metadata)
        media_type = str(raw_artifact.get("media_type") or fallback_media_type)
        checksum = _artifact_checksum(uri, metadata)
        size_bytes = _artifact_size_bytes(uri, metadata)
        checksum_source = "artifact_content" if _has_content_checksum(metadata) else "artifact_uri"
        descriptors.append(
            ArtifactDescriptor(
                name=name,
                artifact_type=artifact_type,
                uri=uri,
                media_type=media_type,
                size_bytes=size_bytes,
                checksum_sha256=checksum,
                metadata={**metadata, "checksum_source": checksum_source},
            )
        )
    if descriptors:
        return tuple(descriptors)
    return (
        _reference_artifact_descriptor(
            name=fallback_name,
            artifact_type=fallback_type,
            uri=fallback_uri,
            media_type=fallback_media_type,
        ),
    )


def _reference_artifact_descriptor(
    *,
    name: str,
    artifact_type: str,
    uri: str,
    media_type: str,
) -> ArtifactDescriptor:
    encoded_uri = uri.strip().encode("utf-8")
    return ArtifactDescriptor(
        name=name,
        artifact_type=artifact_type,
        uri=uri,
        media_type=media_type,
        size_bytes=len(encoded_uri),
        checksum_sha256=sha256_uri(encoded_uri),
        metadata={"checksum_source": "artifact_uri"},
    )


def _manifest_to_payload(manifest: ArtifactManifest) -> dict[str, object]:
    return {
        "schema_version": manifest.schema_version,
        "artifact_set_type": manifest.artifact_set_type,
        "artifact_set_id": manifest.artifact_set_id,
        "artifact_root_uri": manifest.artifact_root_uri,
        "producer": manifest.producer,
        "created_at": manifest.created_at.astimezone(UTC).isoformat(),
        "artifacts": [
            {
                "name": artifact.name,
                "artifact_type": artifact.artifact_type,
                "uri": artifact.uri,
                "media_type": artifact.media_type,
                "size_bytes": artifact.size_bytes,
                "checksum_sha256": artifact.checksum_sha256,
                "metadata": artifact.metadata,
            }
            for artifact in manifest.artifacts
        ],
        "lineage": [
            {
                "source_type": reference.source_type,
                "source_id": reference.source_id,
                "relation": reference.relation,
            }
            for reference in manifest.lineage
        ],
        "metadata": manifest.metadata,
    }


def _validate_artifact_descriptor(artifact: ArtifactDescriptor) -> None:
    if not artifact.name.strip():
        raise DomainValidationError("Artifact descriptor name is required.")
    if not artifact.artifact_type.strip():
        raise DomainValidationError("Artifact descriptor type is required.")
    if not artifact.uri.strip():
        raise DomainValidationError("Artifact descriptor URI is required.")
    if not artifact.media_type.strip():
        raise DomainValidationError("Artifact descriptor media type is required.")
    if artifact.size_bytes < 0:
        raise DomainValidationError("Artifact descriptor size cannot be negative.")
    normalize_sha256(artifact.checksum_sha256)


def _validate_lineage_reference(reference: ArtifactLineageReference) -> None:
    if not reference.source_type.strip():
        raise DomainValidationError("Artifact lineage source type is required.")
    if not reference.source_id.strip():
        raise DomainValidationError("Artifact lineage source ID is required.")
    if not reference.relation.strip():
        raise DomainValidationError("Artifact lineage relation is required.")


def _metadata(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in value.items()}


def _artifact_uri(raw_artifact: dict[str, object], metadata: dict[str, object]) -> str:
    control_plane_uri = metadata.get("control_plane_uri")
    if isinstance(control_plane_uri, str) and control_plane_uri.strip():
        return control_plane_uri.strip()
    uri = raw_artifact.get("uri")
    if isinstance(uri, str) and uri.strip():
        return uri.strip()
    raise DomainValidationError("Training artifact metadata must include a URI.")


def _artifact_checksum(uri: str, metadata: dict[str, object]) -> str:
    for key in ("checksum_sha256", "sha256", "content_hash"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return normalize_sha256(value)
    return sha256_uri(uri.encode("utf-8"))


def _artifact_size_bytes(uri: str, metadata: dict[str, object]) -> int:
    value = metadata.get("size_bytes")
    if isinstance(value, int) and value >= 0:
        return value
    return len(uri.encode("utf-8"))


def _has_content_checksum(metadata: dict[str, object]) -> bool:
    return any(
        isinstance(metadata.get(key), str) and str(metadata[key]).strip()
        for key in ("checksum_sha256", "sha256", "content_hash")
    )


def _model_media_type(model_format: str) -> str:
    if model_format == "mlflow":
        return "application/vnd.mlflow.model"
    if model_format == "onnx":
        return "application/x-onnx"
    if model_format in {"xgboost-booster", "lightgbm-booster"}:
        return "application/octet-stream"
    if model_format in {"torchscript", "safetensors"}:
        return "application/octet-stream"
    return "application/octet-stream"


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)
