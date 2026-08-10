from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol

from forgeml.platform.artifacts.manifest import (
    ArtifactManifest,
    serialize_artifact_manifest,
    sha256_uri,
    validate_payload_checksum,
)
from forgeml.platform.domain.errors import DomainValidationError, ResourceNotFoundError


@dataclass(frozen=True)
class StoredArtifact:
    key: str
    uri: str
    content_type: str
    size_bytes: int
    checksum_sha256: str


class ArtifactStorageGateway(Protocol):
    def put_bytes(self, *, key: str, payload: bytes, content_type: str) -> StoredArtifact:
        raise NotImplementedError

    def get_bytes(self, *, key: str) -> bytes:
        raise NotImplementedError

    def exists(self, *, key: str) -> bool:
        raise NotImplementedError


class ArtifactManifestWriter(Protocol):
    def put_manifest(self, *, key: str, manifest: ArtifactManifest) -> StoredArtifact:
        raise NotImplementedError


class ArtifactManifestStore:
    def __init__(self, gateway: ArtifactStorageGateway) -> None:
        self._gateway = gateway

    def put_manifest(self, *, key: str, manifest: ArtifactManifest) -> StoredArtifact:
        payload = serialize_artifact_manifest(manifest)
        stored = self._gateway.put_bytes(
            key=key,
            payload=payload,
            content_type="application/vnd.forgeml.artifact-manifest+json",
        )
        validate_payload_checksum(payload, stored.checksum_sha256)
        return stored


class LocalArtifactStorageGateway:
    def __init__(self, *, root: Path, bucket: str, uri_scheme: str = "s3") -> None:
        self._root = root
        self._bucket = bucket.strip()
        self._uri_scheme = uri_scheme.strip()
        if not self._bucket:
            raise ValueError("Artifact storage bucket is required.")
        if not self._uri_scheme:
            raise ValueError("Artifact storage URI scheme is required.")

    def put_bytes(self, *, key: str, payload: bytes, content_type: str) -> StoredArtifact:
        safe_key = _normalize_key(key)
        target = self._root / safe_key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        checksum = sha256_uri(payload)
        return StoredArtifact(
            key=safe_key,
            uri=self._uri_for_key(safe_key),
            content_type=content_type,
            size_bytes=len(payload),
            checksum_sha256=checksum,
        )

    def get_bytes(self, *, key: str) -> bytes:
        safe_key = _normalize_key(key)
        target = self._root / safe_key
        if not target.is_file():
            raise ResourceNotFoundError("Artifact object was not found.")
        return target.read_bytes()

    def exists(self, *, key: str) -> bool:
        return (self._root / _normalize_key(key)).is_file()

    def _uri_for_key(self, key: str) -> str:
        return f"{self._uri_scheme}://{self._bucket}/{key}"


class InMemoryArtifactStorageGateway:
    def __init__(self, *, bucket: str = "forgeml-artifacts", uri_scheme: str = "s3") -> None:
        self._bucket = bucket
        self._uri_scheme = uri_scheme
        self._objects: dict[str, StoredArtifact] = {}
        self._payloads: dict[str, bytes] = {}

    def put_bytes(self, *, key: str, payload: bytes, content_type: str) -> StoredArtifact:
        safe_key = _normalize_key(key)
        stored = StoredArtifact(
            key=safe_key,
            uri=f"{self._uri_scheme}://{self._bucket}/{safe_key}",
            content_type=content_type,
            size_bytes=len(payload),
            checksum_sha256=sha256_uri(payload),
        )
        self._objects[safe_key] = stored
        self._payloads[safe_key] = bytes(payload)
        return stored

    def get_bytes(self, *, key: str) -> bytes:
        safe_key = _normalize_key(key)
        if safe_key not in self._payloads:
            raise ResourceNotFoundError("Artifact object was not found.")
        return self._payloads[safe_key]

    def exists(self, *, key: str) -> bool:
        return _normalize_key(key) in self._payloads


def _normalize_key(key: str) -> str:
    raw_key = key.strip()
    if not raw_key:
        raise DomainValidationError("Artifact storage key is required.")
    path = PurePosixPath(raw_key)
    if path.is_absolute() or ".." in path.parts:
        raise DomainValidationError("Artifact storage key must be a relative object key.")
    normalized = path.as_posix()
    if normalized in {"", "."}:
        raise DomainValidationError("Artifact storage key is required.")
    return normalized
