"""Immutable lineage linking normalized artifacts to verified Raw inputs."""

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Dict, Iterable, Mapping, Tuple

from stock_quant.data.bars import DAILY_BAR_SCHEMA_VERSION
from stock_quant.data.quality import QualityReport
from stock_quant.data.raw import (
    ArtifactIntegrityError,
    InvalidArtifactError,
    RawArtifactRef,
    RawArtifactStore,
)
from stock_quant.data.storage import DailyBarParquetStore, NormalizedArtifactRef


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


@dataclass(frozen=True)
class LineageRecord:
    lineage_id: str
    normalized_artifact_id: str
    normalized_content_hash: str
    raw_artifact_ids: Tuple[str, ...]
    transform_name: str
    transform_version: str
    schema_version: str
    code_identity: str
    config_identity: str
    quality_report_id: str
    quality_passed: bool

    def canonical(self, *, include_id: bool) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "code_identity": self.code_identity,
            "config_identity": self.config_identity,
            "normalized_artifact_id": self.normalized_artifact_id,
            "normalized_content_hash": self.normalized_content_hash,
            "quality_passed": self.quality_passed,
            "quality_report_id": self.quality_report_id,
            "raw_artifact_ids": list(self.raw_artifact_ids),
            "schema_version": self.schema_version,
            "transform_name": self.transform_name,
            "transform_version": self.transform_version,
        }
        if include_id:
            result["lineage_id"] = self.lineage_id
        return result


class LineageStore:
    """Append-only lineage store that verifies all parents before publication."""

    def __init__(
        self,
        root: Path,
        *,
        raw_store: RawArtifactStore,
        normalized_store: DailyBarParquetStore,
    ) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.raw_store = raw_store
        self.normalized_store = normalized_store

    def put(
        self,
        normalized_ref: NormalizedArtifactRef,
        raw_refs: Iterable[RawArtifactRef],
        *,
        transform_name: str,
        transform_version: str,
        code_identity: str,
        config_identity: str,
        quality_report: QualityReport,
    ) -> LineageRecord:
        self._validate_name(transform_name, "transform_name")
        self._validate_name(transform_version, "transform_version")
        self._validate_hash(code_identity, "code_identity")
        self._validate_hash(config_identity, "config_identity")
        if not isinstance(quality_report, QualityReport):
            raise TypeError("quality_report must be a QualityReport")
        expected_quality = QualityReport.from_issues(quality_report.issues)
        if expected_quality.report_id != quality_report.report_id:
            raise ArtifactIntegrityError("quality report identity mismatch")

        verified_raw = tuple(sorted(raw_refs, key=lambda ref: ref.artifact_id))
        if not verified_raw:
            raise InvalidArtifactError("lineage requires at least one Raw parent")
        raw_ids = tuple(ref.artifact_id for ref in verified_raw)
        if len(set(raw_ids)) != len(raw_ids):
            raise InvalidArtifactError("lineage Raw parents cannot contain duplicates")
        if normalized_ref.source_raw_artifact_id not in raw_ids:
            raise InvalidArtifactError("normalized direct Raw parent is missing")
        for raw_ref in verified_raw:
            content = self.raw_store.read(raw_ref.artifact_id)
            if hashlib.sha256(content).hexdigest() != raw_ref.content_hash:
                raise ArtifactIntegrityError("Raw reference content hash mismatch")
        self.normalized_store.read(normalized_ref)

        fields = {
            "code_identity": code_identity,
            "config_identity": config_identity,
            "normalized_artifact_id": normalized_ref.artifact_id,
            "normalized_content_hash": normalized_ref.content_hash,
            "quality_passed": quality_report.passed,
            "quality_report_id": quality_report.report_id,
            "raw_artifact_ids": list(raw_ids),
            "schema_version": DAILY_BAR_SCHEMA_VERSION,
            "transform_name": transform_name,
            "transform_version": transform_version,
        }
        lineage_id = hashlib.sha256(_canonical_json(fields)).hexdigest()
        record = LineageRecord(
            lineage_id=lineage_id,
            normalized_artifact_id=normalized_ref.artifact_id,
            normalized_content_hash=normalized_ref.content_hash,
            raw_artifact_ids=raw_ids,
            transform_name=transform_name,
            transform_version=transform_version,
            schema_version=DAILY_BAR_SCHEMA_VERSION,
            code_identity=code_identity,
            config_identity=config_identity,
            quality_report_id=quality_report.report_id,
            quality_passed=quality_report.passed,
        )
        self._publish(record)
        return record

    def read(self, lineage_id: str) -> LineageRecord:
        self._validate_hash(lineage_id, "lineage_id")
        target = self._path(lineage_id)
        try:
            raw = target.read_bytes()
            payload = json.loads(raw)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            raise ArtifactIntegrityError("lineage record missing or unreadable") from exc
        claimed = payload.pop("lineage_id", None)
        if claimed != lineage_id or hashlib.sha256(
            _canonical_json(payload)
        ).hexdigest() != lineage_id:
            raise ArtifactIntegrityError("lineage record identity mismatch")
        try:
            record = LineageRecord(
                lineage_id=lineage_id,
                normalized_artifact_id=payload["normalized_artifact_id"],
                normalized_content_hash=payload["normalized_content_hash"],
                raw_artifact_ids=tuple(payload["raw_artifact_ids"]),
                transform_name=payload["transform_name"],
                transform_version=payload["transform_version"],
                schema_version=payload["schema_version"],
                code_identity=payload["code_identity"],
                config_identity=payload["config_identity"],
                quality_report_id=payload["quality_report_id"],
                quality_passed=payload["quality_passed"],
            )
        except (KeyError, TypeError) as exc:
            raise ArtifactIntegrityError("lineage record schema mismatch") from exc
        if record.canonical(include_id=True) != json.loads(raw):
            raise ArtifactIntegrityError("lineage record contains invalid field types")
        return record

    def _publish(self, record: LineageRecord) -> None:
        target = self._path(record.lineage_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        expected = _canonical_json(record.canonical(include_id=True))
        if target.exists():
            if target.read_bytes() != expected:
                raise ArtifactIntegrityError("lineage identity collision or tamper")
            return
        descriptor, temp_name = tempfile.mkstemp(prefix=".lineage-", dir=target.parent)
        temp_path = Path(temp_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(expected)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(temp_path, target)
            except FileExistsError:
                if target.read_bytes() != expected:
                    raise ArtifactIntegrityError("lineage identity collision or tamper")
        finally:
            temp_path.unlink(missing_ok=True)

    def _path(self, lineage_id: str) -> Path:
        return self.root / "sha256" / lineage_id[:2] / f"{lineage_id}.json"

    @staticmethod
    def _validate_hash(value: str, name: str) -> None:
        if not isinstance(value, str) or not _SHA256.fullmatch(value):
            raise InvalidArtifactError(f"{name} must be a lowercase SHA-256")

    @staticmethod
    def _validate_name(value: str, name: str) -> None:
        if not isinstance(value, str) or not _SAFE_NAME.fullmatch(value):
            raise InvalidArtifactError(f"invalid {name}: {value!r}")
