import json
from dataclasses import dataclass
from typing import Any
from urllib import error, request
from urllib.parse import urlparse


class ForgeMLApiError(RuntimeError):
    def __init__(
        self,
        status_code: int,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}


@dataclass(frozen=True)
class ForgeMLClient:
    base_url: str = "http://127.0.0.1:8001"
    access_token: str | None = None
    timeout_seconds: float = 30.0

    def with_access_token(self, access_token: str) -> "ForgeMLClient":
        return ForgeMLClient(
            base_url=self.base_url,
            access_token=access_token,
            timeout_seconds=self.timeout_seconds,
        )

    def login(self, email: str, password: str) -> dict[str, Any]:
        return self.post("/api/v1/auth/login", {"email": email, "password": password})

    def me(self) -> dict[str, Any]:
        return self.get("/api/v1/auth/me")

    def list_projects(self) -> dict[str, Any]:
        return self.get("/api/v1/projects")

    def create_project(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.post("/api/v1/projects", payload)

    def list_datasets(self, project_id: str) -> dict[str, Any]:
        return self.get(f"/api/v1/projects/{project_id}/datasets")

    def create_dataset(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.post(f"/api/v1/projects/{project_id}/datasets", payload)

    def list_dataset_versions(self, dataset_id: str) -> dict[str, Any]:
        return self.get(f"/api/v1/datasets/{dataset_id}/versions")

    def create_dataset_version(self, dataset_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.post(f"/api/v1/datasets/{dataset_id}/versions", payload)

    def finalize_dataset_version(self, version_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.post(f"/api/v1/dataset-versions/{version_id}/finalize", payload)

    def validate_dataset_version(self, version_id: str) -> dict[str, Any]:
        return self.post(f"/api/v1/dataset-versions/{version_id}/validate", {})

    def list_feature_sets(self, project_id: str) -> dict[str, Any]:
        return self.get(f"/api/v1/projects/{project_id}/feature-sets")

    def create_feature_set(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.post(f"/api/v1/projects/{project_id}/feature-sets", payload)

    def list_feature_definitions(self, feature_set_id: str) -> dict[str, Any]:
        return self.get(f"/api/v1/feature-sets/{feature_set_id}/features")

    def register_feature_definitions(
        self,
        feature_set_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return self.post(f"/api/v1/feature-sets/{feature_set_id}/features", payload)

    def list_feature_pipelines(self, feature_set_id: str) -> dict[str, Any]:
        return self.get(f"/api/v1/feature-sets/{feature_set_id}/pipelines")

    def register_feature_pipeline(
        self,
        feature_set_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return self.post(f"/api/v1/feature-sets/{feature_set_id}/pipelines", payload)

    def materialize_feature_pipeline(self, pipeline_id: str) -> dict[str, Any]:
        return self.post(f"/api/v1/feature-pipelines/{pipeline_id}/materialize", {})

    def list_experiments(self, project_id: str) -> dict[str, Any]:
        return self.get(f"/api/v1/projects/{project_id}/experiments")

    def create_experiment(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.post(f"/api/v1/projects/{project_id}/experiments", payload)

    def list_training_runs(self, project_id: str) -> dict[str, Any]:
        return self.get(f"/api/v1/projects/{project_id}/training-runs")

    def start_training_run(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.post(f"/api/v1/projects/{project_id}/training-runs", payload)

    def record_training_result(
        self,
        training_run_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return self.post(f"/api/v1/training-runs/{training_run_id}/result", payload)

    def list_registered_models(self, project_id: str) -> dict[str, Any]:
        return self.get(f"/api/v1/projects/{project_id}/models")

    def create_registered_model(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.post(f"/api/v1/projects/{project_id}/models", payload)

    def list_model_versions(self, model_id: str) -> dict[str, Any]:
        return self.get(f"/api/v1/models/{model_id}/versions")

    def get_model_version(self, version_id: str) -> dict[str, Any]:
        return self.get(f"/api/v1/model-versions/{version_id}")

    def register_model_version(self, model_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.post(f"/api/v1/models/{model_id}/versions", payload)

    def request_model_approval(self, version_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.post(f"/api/v1/model-versions/{version_id}/approval-request", payload)

    def review_model_version(self, version_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.post(f"/api/v1/model-versions/{version_id}/review", payload)

    def list_deployments(self, project_id: str) -> dict[str, Any]:
        return self.get(f"/api/v1/projects/{project_id}/deployments")

    def create_deployment(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.post(f"/api/v1/projects/{project_id}/deployments", payload)

    def list_deployment_revisions(self, deployment_id: str) -> dict[str, Any]:
        return self.get(f"/api/v1/deployments/{deployment_id}/revisions")

    def create_deployment_revision(
        self,
        deployment_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return self.post(f"/api/v1/deployments/{deployment_id}/revisions", payload)

    def record_deployment_health(self, revision_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.post(f"/api/v1/deployment-revisions/{revision_id}/health-checks", payload)

    def list_inference_endpoints(self, project_id: str) -> dict[str, Any]:
        return self.get(f"/api/v1/projects/{project_id}/inference-endpoints")

    def create_inference_endpoint(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.post(f"/api/v1/projects/{project_id}/inference-endpoints", payload)

    def list_inference_requests(self, endpoint_id: str) -> dict[str, Any]:
        return self.get(f"/api/v1/inference-endpoints/{endpoint_id}/requests")

    def predict(self, endpoint_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.post(f"/api/v1/inference-endpoints/{endpoint_id}/predict", payload)

    def record_inference_metric_snapshot(
        self,
        endpoint_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return self.post(f"/api/v1/inference-endpoints/{endpoint_id}/metric-snapshots", payload)

    def list_drift_profiles(self, project_id: str) -> dict[str, Any]:
        return self.get(f"/api/v1/projects/{project_id}/drift-profiles")

    def create_drift_profile(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.post(f"/api/v1/projects/{project_id}/drift-profiles", payload)

    def list_drift_reports(self, project_id: str) -> dict[str, Any]:
        return self.get(f"/api/v1/projects/{project_id}/drift-reports")

    def run_drift_report(self, profile_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.post(f"/api/v1/drift-profiles/{profile_id}/reports", payload)

    def list_alert_rules(self, project_id: str) -> dict[str, Any]:
        return self.get(f"/api/v1/projects/{project_id}/alert-rules")

    def create_alert_rule(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.post(f"/api/v1/projects/{project_id}/alert-rules", payload)

    def evaluate_alert_rule(self, rule_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.post(f"/api/v1/alert-rules/{rule_id}/evaluate", payload)

    def list_retraining_policies(self, project_id: str) -> dict[str, Any]:
        return self.get(f"/api/v1/projects/{project_id}/retraining-policies")

    def create_retraining_policy(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.post(f"/api/v1/projects/{project_id}/retraining-policies", payload)

    def evaluate_retraining_policy(self, policy_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.post(f"/api/v1/retraining-policies/{policy_id}/evaluate", payload)

    def get(self, path: str) -> dict[str, Any]:
        return self._request("GET", path)

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", path, payload)

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"accept": "application/json"}
        if body is not None:
            headers["content-type"] = "application/json"
        if self.access_token:
            headers["authorization"] = f"Bearer {self.access_token}"
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        parsed_url = urlparse(url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ValueError("ForgeML API base_url must resolve to an http or https URL")
        api_request = request.Request(  # noqa: S310
            url,
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with request.urlopen(api_request, timeout=self.timeout_seconds) as response:  # noqa: S310
                response_body = response.read().decode("utf-8")
                return json.loads(response_body) if response_body else {}
        except error.HTTPError as exc:
            response_body = exc.read().decode("utf-8")
            payload_data = json.loads(response_body) if response_body else {}
            detail = payload_data.get("detail") if isinstance(payload_data, dict) else None
            message = str(detail or f"ForgeML API request failed with status {exc.code}")
            raise ForgeMLApiError(exc.code, message, payload_data) from exc
