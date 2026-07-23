import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID


@dataclass(frozen=True)
class LocalUploadInstructions:
    upload_url: str
    object_uri: str
    expires_at: str
    required_headers: dict[str, str]


class LocalObjectStorageGateway:
    def __init__(
        self,
        *,
        endpoint: str,
        bucket: str,
        signing_secret: str,
        ttl_minutes: int = 15,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._bucket = bucket
        self._signing_secret = signing_secret.encode()
        self._ttl_minutes = ttl_minutes

    def create_upload_instructions(
        self,
        *,
        organization_id: UUID,
        project_id: UUID,
        dataset_id: UUID,
        version_id: UUID,
        filename: str,
        content_type: str,
    ) -> LocalUploadInstructions:
        expires_at = datetime.now(UTC) + timedelta(minutes=self._ttl_minutes)
        object_key = (
            f"organizations/{organization_id}/projects/{project_id}/datasets/{dataset_id}/"
            f"versions/{version_id}/{_safe_filename(filename)}"
        )
        object_uri = f"s3://{self._bucket}/{object_key}"
        signature = hmac.new(
            self._signing_secret,
            f"{object_key}:{content_type}:{int(expires_at.timestamp())}".encode(),
            hashlib.sha256,
        ).hexdigest()
        upload_url = (
            f"{self._endpoint}/{self._bucket}/{object_key}"
            f"?expires={int(expires_at.timestamp())}&signature={signature}"
        )
        return LocalUploadInstructions(
            upload_url=upload_url,
            object_uri=object_uri,
            expires_at=expires_at.isoformat(),
            required_headers={"content-type": content_type},
        )


def _safe_filename(filename: str) -> str:
    import re

    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "-", filename.strip()).strip("-")
    return sanitized or "dataset.csv"

