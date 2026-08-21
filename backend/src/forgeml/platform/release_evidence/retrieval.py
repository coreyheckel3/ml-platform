from __future__ import annotations

import io
import json
import zipfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib import parse, request

RELEASE_MANIFEST_ARTIFACT_NAME = "forgeml-release-manifest"
RELEASE_MANIFEST_SCHEMA_VERSION = "forgeml.release_manifest.v1"
RELEASE_EVIDENCE_RETRIEVAL_SCHEMA_VERSION = "forgeml.release_evidence_retrieval.v1"
DEFAULT_GITHUB_API_ROOT = "https://api.github.com"
RELEASE_EVIDENCE_REQUIRED_ARTIFACTS: tuple[str, ...] = (
    "airflow_orchestration_contract",
    "alembic_migration_contract",
    "api_authorization_contract",
    "architecture_walkthrough",
    "artifact_manifest_contract",
    "ci_runtime_contract",
    "demo_readiness_contract",
    "demo_readiness_runbook",
    "deployment_runtime_contract",
    "docker_compose",
    "external_training_package_contract",
    "github_actions_ci",
    "mlflow_tracking_contract",
    "monitoring_dashboard_contract",
    "openapi_contract",
    "operational_audit_ux_contract",
    "permission_catalog",
    "portfolio_architecture_diagrams",
    "portfolio_evidence_map",
    "portfolio_readiness_contract",
    "portfolio_resume_bullets",
    "portfolio_reviewer_guide",
    "portfolio_screenshot_catalog",
    "problem_details_contract",
    "production_readiness_runbook",
    "release_evidence_drilldown_api_contract",
    "release_evidence_notifications_contract",
    "release_evidence_retrieval_contract",
    "release_evidence_scheduled_refresh_contract",
    "release_evidence_ux_contract",
    "release_evidence_workflow_contract",
    "release_manifest_contract",
    "release_manifest_verification_contract",
    "release_smoke_contract",
    "request_log_event_contract",
    "runtime_config_policy",
    "security_hardening_contract",
    "sqlalchemy_schema_contract",
    "staging_terraform_main",
    "staging_terraform_variables",
)
RELEASE_EVIDENCE_REQUIRED_QUALITY_GATES: tuple[str, ...] = (
    "airflow_orchestration_contract",
    "artifact_manifest_contract",
    "backend_lint",
    "backend_tests",
    "ci_runtime_contract",
    "demo_readiness_contract",
    "deployment_runtime_contract",
    "docker_build",
    "example_training_smoke",
    "external_training_package_contract",
    "frontend_bundle_budget",
    "frontend_e2e",
    "frontend_lint",
    "frontend_tests",
    "mlflow_tracking_contract",
    "monitoring_dashboard_contract",
    "operational_audit_ux_contract",
    "portfolio_readiness_contract",
    "production_readiness",
    "release_evidence_drilldown_api_contract",
    "release_evidence_notifications_contract",
    "release_evidence_retrieval_contract",
    "release_evidence_scheduled_refresh_contract",
    "release_evidence_ux_contract",
    "release_evidence_workflow_contract",
    "release_manifest_contract",
    "release_manifest_verifier_contract",
    "release_smoke_contract",
    "security_hardening_contract",
)

JsonTransport = Callable[[str, Mapping[str, str], float], Mapping[str, Any]]
BytesTransport = Callable[[str, Mapping[str, str], float], bytes]


class ReleaseEvidenceRetrievalError(RuntimeError):
    """Raised when live release evidence cannot be located or parsed."""


@dataclass(frozen=True)
class ReleaseEvidenceRun:
    id: int
    head_sha: str
    branch: str
    status: str
    conclusion: str
    html_url: str


@dataclass(frozen=True)
class ReleaseEvidenceArtifact:
    id: int
    name: str
    size_in_bytes: int
    archive_download_url: str


@dataclass(frozen=True)
class ReleaseEvidenceManifestSummary:
    schema_version: str | None
    git_sha: str | None
    git_branch: str | None
    artifact_names: tuple[str, ...]
    quality_gate_names: tuple[str, ...]
    image_target_names: tuple[str, ...]
    ci_run_url: str | None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReleaseEvidenceComparison:
    schema_version_matches: bool
    branch_matches: bool
    required_artifacts_present: bool
    required_quality_gates_present: bool
    ci_evidence_present: bool
    expected_schema_version: str
    expected_branch: str | None
    manifest_git_sha: str | None
    manifest_git_branch: str | None
    artifact_count: int
    quality_gate_count: int
    missing_artifacts: tuple[str, ...]
    missing_quality_gates: tuple[str, ...]
    ci_run_url: str | None

    @property
    def passed(self) -> bool:
        return (
            self.schema_version_matches
            and self.branch_matches
            and self.required_artifacts_present
            and self.required_quality_gates_present
            and self.ci_evidence_present
        )

    def as_dict(self) -> dict[str, Any]:
        return {**asdict(self), "passed": self.passed}


class ReleaseEvidenceGateway(Protocol):
    def latest_successful_run(self) -> ReleaseEvidenceRun:
        raise NotImplementedError

    def download_release_manifest(
        self,
        run: ReleaseEvidenceRun,
    ) -> dict[str, Any]:
        raise NotImplementedError


class GitHubActionsReleaseEvidenceGateway:
    def __init__(
        self,
        *,
        repository: str,
        token: str | None,
        branch: str = "main",
        workflow_file: str = "ci.yml",
        artifact_name: str = RELEASE_MANIFEST_ARTIFACT_NAME,
        api_root: str = DEFAULT_GITHUB_API_ROOT,
        timeout_seconds: float = 15.0,
        json_transport: JsonTransport | None = None,
        bytes_transport: BytesTransport | None = None,
    ) -> None:
        if "/" not in repository:
            raise ReleaseEvidenceRetrievalError(
                "GitHub repository must use owner/name format."
            )
        self.repository = repository
        self.token = token
        self.branch = branch
        self.workflow_file = workflow_file
        self.artifact_name = artifact_name
        self.api_root = api_root.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._json_transport = json_transport or _urllib_json_transport
        self._bytes_transport = bytes_transport or _urllib_bytes_transport

    def latest_successful_run(self) -> ReleaseEvidenceRun:
        query = parse.urlencode(
            {
                "branch": self.branch,
                "status": "success",
                "event": "push",
                "per_page": "1",
            }
        )
        payload = self._get_json(
            f"/repos/{self.repository}/actions/workflows/{self.workflow_file}/runs?{query}"
        )
        runs = payload.get("workflow_runs")
        if not isinstance(runs, list) or not runs:
            raise ReleaseEvidenceRetrievalError(
                f"No successful {self.workflow_file} runs found on {self.branch}."
            )
        run = _as_mapping(runs[0], "workflow run")
        return ReleaseEvidenceRun(
            id=_as_int(run.get("id"), "workflow run id"),
            head_sha=_as_string(run.get("head_sha"), "workflow run head_sha"),
            branch=_as_string(run.get("head_branch"), "workflow run head_branch"),
            status=_as_string(run.get("status"), "workflow run status"),
            conclusion=_as_string(run.get("conclusion"), "workflow run conclusion"),
            html_url=_as_string(run.get("html_url"), "workflow run html_url"),
        )

    def list_artifacts(self, run: ReleaseEvidenceRun) -> tuple[ReleaseEvidenceArtifact, ...]:
        payload = self._get_json(
            f"/repos/{self.repository}/actions/runs/{run.id}/artifacts?per_page=100"
        )
        artifacts = payload.get("artifacts")
        if not isinstance(artifacts, list):
            raise ReleaseEvidenceRetrievalError(
                "GitHub artifact response is missing artifacts list."
            )
        return tuple(_artifact_from_payload(item) for item in artifacts)

    def download_release_manifest(
        self,
        run: ReleaseEvidenceRun,
    ) -> dict[str, Any]:
        artifact = self._find_release_manifest_artifact(run)
        archive_bytes = self._get_bytes(artifact.archive_download_url)
        return _manifest_from_zip(archive_bytes, self.artifact_name)

    def retrieve_latest_manifest(self) -> tuple[ReleaseEvidenceRun, dict[str, Any]]:
        run = self.latest_successful_run()
        return run, self.download_release_manifest(run)

    def _find_release_manifest_artifact(
        self,
        run: ReleaseEvidenceRun,
    ) -> ReleaseEvidenceArtifact:
        artifacts = self.list_artifacts(run)
        for artifact in artifacts:
            if artifact.name == self.artifact_name:
                return artifact
        artifact_names = ", ".join(artifact.name for artifact in artifacts) or "none"
        raise ReleaseEvidenceRetrievalError(
            f"Release manifest artifact {self.artifact_name!r} was not found. "
            f"Available artifacts: {artifact_names}."
        )

    def _get_json(self, path_or_url: str) -> Mapping[str, Any]:
        return self._json_transport(
            self._url(path_or_url),
            self._headers(),
            self.timeout_seconds,
        )

    def _get_bytes(self, path_or_url: str) -> bytes:
        return self._bytes_transport(
            self._url(path_or_url),
            self._headers(),
            self.timeout_seconds,
        )

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ForgeML-release-evidence-retriever",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _url(self, path_or_url: str) -> str:
        if path_or_url.startswith("https://") or path_or_url.startswith("http://"):
            return path_or_url
        return f"{self.api_root}/{path_or_url.lstrip('/')}"


class LocalReleaseEvidenceGateway:
    def __init__(self, manifest_path: Path, *, branch: str = "local") -> None:
        self.manifest_path = manifest_path
        self.branch = branch

    def latest_successful_run(self) -> ReleaseEvidenceRun:
        manifest = self.download_release_manifest(
            ReleaseEvidenceRun(
                id=0,
                head_sha="local",
                branch=self.branch,
                status="completed",
                conclusion="success",
                html_url=self.manifest_path.as_posix(),
            )
        )
        summary = summarize_release_manifest(manifest)
        return ReleaseEvidenceRun(
            id=0,
            head_sha=summary.git_sha or "local",
            branch=summary.git_branch or self.branch,
            status="completed",
            conclusion="success",
            html_url=summary.ci_run_url or self.manifest_path.as_posix(),
        )

    def download_release_manifest(
        self,
        run: ReleaseEvidenceRun,
    ) -> dict[str, Any]:
        if not self.manifest_path.is_file():
            raise ReleaseEvidenceRetrievalError(
                f"Release manifest does not exist: {self.manifest_path}"
            )
        payload = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ReleaseEvidenceRetrievalError("Release manifest root must be an object.")
        return payload


def summarize_release_manifest(
    manifest: Mapping[str, Any],
) -> ReleaseEvidenceManifestSummary:
    release = _optional_mapping(manifest.get("release"))
    source = _optional_mapping(manifest.get("source"))
    return ReleaseEvidenceManifestSummary(
        schema_version=_optional_string(manifest.get("schema_version")),
        git_sha=_optional_string(source.get("git_sha")) if source else None,
        git_branch=_optional_string(source.get("git_branch")) if source else None,
        artifact_names=_named_items(manifest.get("artifacts")),
        quality_gate_names=_named_items(manifest.get("quality_gates")),
        image_target_names=_named_items(manifest.get("images")),
        ci_run_url=_optional_string(release.get("ci_run_url")) if release else None,
    )


def compare_release_manifest_to_contract(
    manifest: Mapping[str, Any],
    *,
    required_artifacts: Sequence[str],
    required_quality_gates: Sequence[str],
    expected_schema_version: str = RELEASE_MANIFEST_SCHEMA_VERSION,
    expected_branch: str | None = "main",
) -> ReleaseEvidenceComparison:
    summary = summarize_release_manifest(manifest)
    artifact_set = set(summary.artifact_names)
    quality_gate_set = set(summary.quality_gate_names)
    missing_artifacts = tuple(sorted(set(required_artifacts) - artifact_set))
    missing_quality_gates = tuple(sorted(set(required_quality_gates) - quality_gate_set))
    branch_matches = expected_branch is None or summary.git_branch == expected_branch

    return ReleaseEvidenceComparison(
        schema_version_matches=summary.schema_version == expected_schema_version,
        branch_matches=branch_matches,
        required_artifacts_present=not missing_artifacts,
        required_quality_gates_present=not missing_quality_gates,
        ci_evidence_present=bool(summary.ci_run_url),
        expected_schema_version=expected_schema_version,
        expected_branch=expected_branch,
        manifest_git_sha=summary.git_sha,
        manifest_git_branch=summary.git_branch,
        artifact_count=len(summary.artifact_names),
        quality_gate_count=len(summary.quality_gate_names),
        missing_artifacts=missing_artifacts,
        missing_quality_gates=missing_quality_gates,
        ci_run_url=summary.ci_run_url,
    )


def _artifact_from_payload(payload: object) -> ReleaseEvidenceArtifact:
    artifact = _as_mapping(payload, "artifact")
    return ReleaseEvidenceArtifact(
        id=_as_int(artifact.get("id"), "artifact id"),
        name=_as_string(artifact.get("name"), "artifact name"),
        size_in_bytes=_as_int(artifact.get("size_in_bytes"), "artifact size"),
        archive_download_url=_as_string(
            artifact.get("archive_download_url"),
            "artifact archive_download_url",
        ),
    )


def _manifest_from_zip(archive_bytes: bytes, artifact_name: str) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            candidate_names = [
                name
                for name in archive.namelist()
                if name.endswith(".json")
                and (artifact_name in name or "release-manifest" in name)
            ]
            if not candidate_names:
                candidate_names = [name for name in archive.namelist() if name.endswith(".json")]
            if not candidate_names:
                raise ReleaseEvidenceRetrievalError(
                    "Release evidence artifact archive does not contain a JSON manifest."
                )
            with archive.open(sorted(candidate_names)[0]) as manifest_file:
                payload = json.loads(manifest_file.read().decode("utf-8"))
    except zipfile.BadZipFile as exc:
        raise ReleaseEvidenceRetrievalError(
            "Release evidence artifact archive is not a valid zip file."
        ) from exc

    if not isinstance(payload, dict):
        raise ReleaseEvidenceRetrievalError("Release manifest root must be an object.")
    return payload


def _urllib_json_transport(
    url: str,
    headers: Mapping[str, str],
    timeout_seconds: float,
) -> Mapping[str, Any]:
    response_bytes = _urllib_bytes_transport(url, headers, timeout_seconds)
    payload = json.loads(response_bytes.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ReleaseEvidenceRetrievalError(f"GitHub API response is not an object: {url}")
    return payload


def _urllib_bytes_transport(
    url: str,
    headers: Mapping[str, str],
    timeout_seconds: float,
) -> bytes:
    api_request = request.Request(url, headers=dict(headers))  # noqa: S310
    with request.urlopen(api_request, timeout=timeout_seconds) as response:  # noqa: S310
        return response.read()


def _named_items(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    names = []
    for item in value:
        if isinstance(item, Mapping) and isinstance(item.get("name"), str):
            names.append(item["name"])
    return tuple(sorted(names))


def _optional_mapping(value: object) -> Mapping[str, Any] | None:
    if isinstance(value, Mapping):
        return value
    return None


def _optional_string(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _as_mapping(value: object, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ReleaseEvidenceRetrievalError(f"{field_name} must be an object.")
    return value


def _as_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ReleaseEvidenceRetrievalError(f"{field_name} must be an integer.")
    return value


def _as_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ReleaseEvidenceRetrievalError(f"{field_name} must be a non-empty string.")
    return value
