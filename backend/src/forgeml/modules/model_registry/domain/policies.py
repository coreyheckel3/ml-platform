import re

from forgeml.modules.model_registry.domain.entities import (
    ModelApprovalStatus,
    ModelVersionStatus,
    TrainingRunPromotionCandidate,
    TrainingRunReference,
)
from forgeml.platform.domain.errors import DomainValidationError

_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")
TRAINING_EXECUTION_SCHEMA_VERSION = "forgeml.training_execution_result.v1"
_ALLOWED_TASK_TYPES = {
    "classification",
    "custom",
    "embedding",
    "ranking",
    "recommendation",
    "regression",
    "retrieval",
}
_ALLOWED_MODEL_FORMATS = {
    "lightgbm-booster",
    "mlflow",
    "onnx",
    "pickle",
    "safetensors",
    "torchscript",
    "xgboost-booster",
}


def build_registered_model_slug(name: str) -> str:
    normalized = _SLUG_PATTERN.sub("-", name.strip().lower()).strip("-")
    if not normalized:
        raise DomainValidationError("Registered model name must contain a letter or number.")
    return normalized[:80]


def validate_registered_model_name(name: str) -> None:
    stripped = name.strip()
    if len(stripped) < 3:
        raise DomainValidationError("Registered model name must be at least 3 characters.")
    if len(stripped) > 120:
        raise DomainValidationError("Registered model name must be at most 120 characters.")


def normalize_task_type(task_type: str) -> str:
    normalized = task_type.strip().lower()
    if normalized not in _ALLOWED_TASK_TYPES:
        allowed = ", ".join(sorted(_ALLOWED_TASK_TYPES))
        raise DomainValidationError(f"Model task type must be one of: {allowed}.")
    return normalized


def normalize_model_format(model_format: str) -> str:
    normalized = model_format.strip().lower()
    if normalized not in _ALLOWED_MODEL_FORMATS:
        allowed = ", ".join(sorted(_ALLOWED_MODEL_FORMATS))
        raise DomainValidationError(f"Model format must be one of: {allowed}.")
    return normalized


def validate_model_signature(signature: dict[str, object]) -> None:
    if len(signature) > 50:
        raise DomainValidationError("Model signature cannot exceed 50 top-level keys.")
    if "inputs" not in signature or "outputs" not in signature:
        raise DomainValidationError("Model signature requires inputs and outputs.")


def validate_training_run_reference(reference: TrainingRunReference) -> None:
    if reference.status != "succeeded":
        raise DomainValidationError("Only succeeded training runs can be registered.")
    if len(reference.artifact_uri.strip()) < 3:
        raise DomainValidationError("Training run must expose a model artifact URI.")


def validate_training_run_promotion_candidate(
    candidate: TrainingRunPromotionCandidate,
) -> None:
    if candidate.status != "succeeded":
        raise DomainValidationError("Only succeeded training runs can be promoted.")
    if len(candidate.artifact_uri.strip()) < 3:
        raise DomainValidationError("Training run must expose a model artifact URI.")
    _training_execution_manifest(candidate)


def model_artifact_uri_from_training_execution(
    candidate: TrainingRunPromotionCandidate,
) -> str:
    manifest = _training_execution_manifest(candidate)
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise DomainValidationError("Training execution manifest must include artifact metadata.")

    model_artifact = next(
        (
            artifact
            for artifact in artifacts
            if isinstance(artifact, dict) and artifact.get("artifact_type") == "model"
        ),
        None,
    )
    if model_artifact is None:
        raise DomainValidationError("Training execution manifest must include a model artifact.")

    metadata = model_artifact.get("metadata")
    metadata_uri = metadata.get("control_plane_uri") if isinstance(metadata, dict) else None
    artifact_uri = metadata_uri or model_artifact.get("uri")
    if not isinstance(artifact_uri, str) or len(artifact_uri.strip()) < 3:
        raise DomainValidationError("Model artifact metadata must include a resolvable URI.")
    return artifact_uri.strip()


def validate_approval_request(version_status: ModelVersionStatus) -> None:
    if version_status != ModelVersionStatus.CANDIDATE:
        raise DomainValidationError("Only candidate model versions can request approval.")


def validate_approval_decision(status: ModelApprovalStatus) -> None:
    if status not in {ModelApprovalStatus.APPROVED, ModelApprovalStatus.REJECTED}:
        raise DomainValidationError("Model review must approve or reject the version.")


def validate_reviewable_status(version_status: ModelVersionStatus) -> None:
    if version_status != ModelVersionStatus.PENDING_APPROVAL:
        raise DomainValidationError("Model version must be pending approval before review.")


def _training_execution_manifest(candidate: TrainingRunPromotionCandidate) -> dict[str, object]:
    manifest = candidate.evaluation_report.get("training_execution")
    if not isinstance(manifest, dict):
        raise DomainValidationError(
            "Training run evaluation report must include a training execution manifest."
        )
    if manifest.get("schema_version") != TRAINING_EXECUTION_SCHEMA_VERSION:
        raise DomainValidationError(
            "Training execution manifest schema version is not supported."
        )
    return manifest
