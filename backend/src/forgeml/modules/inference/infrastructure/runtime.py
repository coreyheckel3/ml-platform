import hashlib
import json
import time

from forgeml.modules.inference.domain.entities import (
    DeploymentRevisionServingReference,
    InferenceHealthProbeResult,
    InferencePredictionResult,
)


class LocalInferenceRuntime:
    def predict(
        self,
        reference: DeploymentRevisionServingReference,
        payload: dict[str, object],
    ) -> InferencePredictionResult:
        started_at = time.perf_counter()
        serialized_payload = json.dumps(payload, sort_keys=True, default=str).encode()
        fingerprint = hashlib.sha256(serialized_payload).hexdigest()
        score = int(fingerprint[:8], 16) / 0xFFFFFFFF
        latency_ms = max((time.perf_counter() - started_at) * 1000, 0.01)
        return InferencePredictionResult(
            output_payload={
                "prediction_id": fingerprint[:16],
                "score": round(score, 6),
                "model_version_id": str(reference.model_version_id),
                "features_seen": len(payload),
                "signature": reference.model_signature,
            },
            latency_ms=latency_ms,
        )

    def health_probe(
        self,
        reference: DeploymentRevisionServingReference,
    ) -> InferenceHealthProbeResult:
        started_at = time.perf_counter()
        status = "healthy" if reference.revision_status == "healthy" else "degraded"
        latency_ms = max((time.perf_counter() - started_at) * 1000, 0.01)
        error_rate = 0.001 if status == "healthy" else 0.05
        return InferenceHealthProbeResult(
            status=status,
            latency_ms=latency_ms,
            error_rate=error_rate,
            details={
                "model_version_id": str(reference.model_version_id),
                "deployment_revision_id": str(reference.deployment_revision_id),
                "traffic_percentage": reference.traffic_percentage,
            },
        )
