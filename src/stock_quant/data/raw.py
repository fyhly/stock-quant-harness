"""Content-addressed, append-only storage for caller-supplied raw bytes."""

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from types import MappingProxyType
from typing import Any, Dict, Mapping


class InvalidArtifactError(ValueError):
    """Raised for invalid metadata or artifact references."""


class ArtifactIntegrityError(RuntimeError):
    """Raised for collisions, corruption, or tampering."""


_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _validate_json(value: Any, path: str = "query") -> None:
    if value is None or isinstance(value, (str, int, bool)):
        return
    if isinstance(value, float):
        raise InvalidArtifactError(f"{path} cannot contain floating-point values")
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                raise InvalidArtifactError(f"{path} keys must be non-empty strings")
            _validate_json(item, f"{path}.{key}")
        return
    raise InvalidArtifactError(f"{path} contains unsupported value {type(value).__name__}")


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def _freeze_json(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    return value


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


@dataclass(frozen=True)
class RawArtifactMetadata:
    """Canonical provenance supplied alongside opaque raw bytes."""

    source: str
    query: Mapping[str, Any]
    fetched_at: datetime
    schema_name: str
    schema_version: str

    def __post_init__(self) -> None:
        for field_name in ("source", "schema_name", "schema_version"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not _SAFE_NAME.fullmatch(value):
                raise InvalidArtifactError(f"invalid {field_name}: {value!r}")
        if not isinstance(self.query, Mapping):
            raise InvalidArtifactError("query must be a mapping")
        query_copy: Dict[str, Any] = dict(self.query)
        _validate_json(query_copy)
        object.__setattr__(self, "query", _freeze_json(query_copy))
        if not isinstance(self.fetched_at, datetime):
            raise InvalidArtifactError("fetched_at must be a datetime")
        if self.fetched_at.tzinfo is None or self.fetched_at.utcoffset() is None:
            raise InvalidArtifactError("fetched_at must be timezone-aware")

    def canonical(self) -> Dict[str, Any]:
        fetched_utc = self.fetched_at.astimezone(timezone.utc)
        return {
            "fetched_at": fetched_utc.isoformat(timespec="microseconds"),
            "query": _thaw_json(self.query),
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "source": self.source,
        }


@dataclass(frozen=True)
class RawArtifactRef:
    artifact_id: str
    content_hash: str
    metadata: RawArtifactMetadata


class RawArtifactStore:
    """Append-only filesystem store with verified, atomic publication."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        if not self.root.is_dir():
            raise InvalidArtifactError("raw store root must be a directory")

    def put(self, content: bytes, metadata: RawArtifactMetadata) -> RawArtifactRef:
        if not isinstance(content, bytes):
            raise TypeError("raw content must be bytes")
        if not isinstance(metadata, RawArtifactMetadata):
            raise TypeError("metadata must be RawArtifactMetadata")
        content_hash = hashlib.sha256(content).hexdigest()
        manifest = self._manifest(metadata, content_hash)
        artifact_id = self._identity(manifest)
        manifest["artifact_id"] = artifact_id
        target = self._artifact_path(artifact_id)
        ref = RawArtifactRef(artifact_id, content_hash, metadata)

        if target.exists():
            self._verify_existing(target, artifact_id, manifest, content)
            return ref

        target.parent.mkdir(parents=True, exist_ok=True)
        temp_path = Path(tempfile.mkdtemp(prefix=".raw-", dir=target.parent))
        try:
            (temp_path / "payload.bin").write_bytes(content)
            (temp_path / "manifest.json").write_bytes(_canonical_json(manifest))
            try:
                os.rename(temp_path, target)
            except OSError:
                if not target.exists():
                    raise
                self._verify_existing(target, artifact_id, manifest, content)
        finally:
            if temp_path.exists():
                shutil.rmtree(temp_path)
        return ref

    def read(self, artifact_id: str) -> bytes:
        if not isinstance(artifact_id, str) or not _SHA256.fullmatch(artifact_id):
            raise InvalidArtifactError("artifact_id must be a lowercase SHA-256")
        target = self._artifact_path(artifact_id)
        try:
            manifest = json.loads((target / "manifest.json").read_text("utf-8"))
            content = (target / "payload.bin").read_bytes()
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            raise ArtifactIntegrityError("artifact is missing or unreadable") from exc
        claimed_id = manifest.pop("artifact_id", None)
        if claimed_id != artifact_id or self._identity(manifest) != artifact_id:
            raise ArtifactIntegrityError("raw manifest identity mismatch")
        if hashlib.sha256(content).hexdigest() != manifest.get("content_hash"):
            raise ArtifactIntegrityError("raw payload content hash mismatch")
        return content

    def _artifact_path(self, artifact_id: str) -> Path:
        return self.root / "sha256" / artifact_id[:2] / artifact_id

    @staticmethod
    def _manifest(
        metadata: RawArtifactMetadata, content_hash: str
    ) -> Dict[str, Any]:
        return {
            "content_hash": content_hash,
            "metadata": metadata.canonical(),
            "manifest_version": "raw-manifest-v1",
        }

    @staticmethod
    def _identity(manifest_without_id: Mapping[str, Any]) -> str:
        return hashlib.sha256(_canonical_json(manifest_without_id)).hexdigest()

    def _verify_existing(
        self,
        target: Path,
        artifact_id: str,
        expected_manifest: Mapping[str, Any],
        expected_content: bytes,
    ) -> None:
        try:
            actual_manifest = (target / "manifest.json").read_bytes()
            actual_content = (target / "payload.bin").read_bytes()
        except FileNotFoundError as exc:
            raise ArtifactIntegrityError("existing raw artifact is incomplete") from exc
        if actual_manifest != _canonical_json(expected_manifest):
            raise ArtifactIntegrityError("artifact identity collision or manifest tamper")
        if actual_content != expected_content:
            raise ArtifactIntegrityError("artifact identity collision or payload tamper")
