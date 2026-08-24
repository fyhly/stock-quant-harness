"""Content-addressed, append-only persistence for Universe snapshots."""

from dataclasses import dataclass
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Dict, Iterable, Mapping, Tuple

from stock_quant.data import ArtifactIntegrityError, InvalidArtifactError
from stock_quant.domain import SecurityId
from stock_quant.universe.engine import SecurityExclusions, UniverseResult
from stock_quant.universe.rules import Exclusion, ExclusionCode


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


@dataclass(frozen=True)
class UniverseSnapshot:
    snapshot_id: str
    as_of: date
    included: Tuple[SecurityId, ...]
    excluded: Tuple[SecurityExclusions, ...]
    rule_version: str
    upstream_identities: Tuple[str, ...]
    code_identity: str
    config_identity: str

    def canonical(self, *, include_id: bool) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "as_of": self.as_of.isoformat(),
            "code_identity": self.code_identity,
            "config_identity": self.config_identity,
            "excluded": [
                {
                    "reasons": [
                        {
                            "code": reason.code.value,
                            "evidence": [list(item) for item in reason.evidence],
                            "message": reason.message,
                            "rule": reason.rule,
                        }
                        for reason in item.reasons
                    ],
                    "security_id": str(item.security_id),
                }
                for item in self.excluded
            ],
            "included": [str(item) for item in self.included],
            "rule_version": self.rule_version,
            "upstream_identities": list(self.upstream_identities),
        }
        if include_id:
            result["snapshot_id"] = self.snapshot_id
        return result


def create_universe_snapshot(
    result: UniverseResult,
    *,
    upstream_identities: Iterable[str],
    code_identity: str,
    config_identity: str,
) -> UniverseSnapshot:
    if not isinstance(result, UniverseResult):
        raise TypeError("result must be a UniverseResult")
    upstream = tuple(sorted(upstream_identities))
    fields: Dict[str, Any] = {
        "as_of": result.as_of.isoformat(),
        "code_identity": code_identity,
        "config_identity": config_identity,
        "excluded": [
            {
                "reasons": [
                    {
                        "code": reason.code.value,
                        "evidence": [list(item) for item in reason.evidence],
                        "message": reason.message,
                        "rule": reason.rule,
                    }
                    for reason in item.reasons
                ],
                "security_id": str(item.security_id),
            }
            for item in result.excluded
        ],
        "included": [str(item) for item in result.included],
        "rule_version": result.rule_version,
        "upstream_identities": list(upstream),
    }
    snapshot_id = hashlib.sha256(_canonical_json(fields)).hexdigest()
    snapshot = UniverseSnapshot(
        snapshot_id,
        result.as_of,
        result.included,
        result.excluded,
        result.rule_version,
        upstream,
        code_identity,
        config_identity,
    )
    _validate_snapshot(snapshot)
    return snapshot


class UniverseSnapshotStore:
    """Atomic no-overwrite local store for validated snapshots."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, snapshot: UniverseSnapshot) -> UniverseSnapshot:
        _validate_snapshot(snapshot)
        target = self._path(snapshot.snapshot_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        expected = _canonical_json(snapshot.canonical(include_id=True))
        if target.exists():
            if target.read_bytes() != expected:
                raise ArtifactIntegrityError("snapshot identity collision or tamper")
            return snapshot
        descriptor, temp_name = tempfile.mkstemp(prefix=".snapshot-", dir=target.parent)
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
                    raise ArtifactIntegrityError("snapshot identity collision or tamper")
        finally:
            temp_path.unlink(missing_ok=True)
        return snapshot

    def read(self, snapshot_id: str) -> UniverseSnapshot:
        _validate_hash(snapshot_id, "snapshot_id")
        target = self._path(snapshot_id)
        try:
            raw = target.read_bytes()
            payload = json.loads(raw)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            raise ArtifactIntegrityError("snapshot missing or unreadable") from exc
        try:
            excluded = tuple(
                SecurityExclusions(
                    SecurityId.parse(item["security_id"]),
                    tuple(
                        Exclusion(
                            ExclusionCode(reason["code"]),
                            reason["rule"],
                            reason["message"],
                            tuple(tuple(pair) for pair in reason["evidence"]),
                        )
                        for reason in item["reasons"]
                    ),
                )
                for item in payload["excluded"]
            )
            snapshot = UniverseSnapshot(
                payload["snapshot_id"],
                date.fromisoformat(payload["as_of"]),
                tuple(SecurityId.parse(item) for item in payload["included"]),
                excluded,
                payload["rule_version"],
                tuple(payload["upstream_identities"]),
                payload["code_identity"],
                payload["config_identity"],
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ArtifactIntegrityError("snapshot schema is invalid") from exc
        try:
            _validate_snapshot(snapshot)
        except (InvalidArtifactError, ValueError) as exc:
            raise ArtifactIntegrityError("snapshot validation failed") from exc
        if snapshot.snapshot_id != snapshot_id:
            raise ArtifactIntegrityError("snapshot path identity mismatch")
        if snapshot.canonical(include_id=True) != json.loads(raw):
            raise ArtifactIntegrityError("snapshot contains noncanonical fields")
        return snapshot

    def _path(self, snapshot_id: str) -> Path:
        return self.root / "sha256" / snapshot_id[:2] / f"{snapshot_id}.json"


def _validate_snapshot(snapshot: UniverseSnapshot) -> None:
    if not isinstance(snapshot, UniverseSnapshot):
        raise TypeError("snapshot must be a UniverseSnapshot")
    _validate_hash(snapshot.snapshot_id, "snapshot_id")
    _validate_hash(snapshot.code_identity, "code_identity")
    _validate_hash(snapshot.config_identity, "config_identity")
    if not snapshot.rule_version.strip():
        raise InvalidArtifactError("snapshot rule_version is required")
    if not snapshot.upstream_identities:
        raise InvalidArtifactError("snapshot requires upstream identities")
    for identity in snapshot.upstream_identities:
        _validate_hash(identity, "upstream identity")
    if snapshot.upstream_identities != tuple(sorted(set(snapshot.upstream_identities))):
        raise InvalidArtifactError("upstream identities must be sorted and unique")
    if snapshot.included != tuple(sorted(set(snapshot.included))):
        raise InvalidArtifactError("included identities must be sorted and unique")
    excluded_ids = tuple(item.security_id for item in snapshot.excluded)
    if excluded_ids != tuple(sorted(set(excluded_ids))):
        raise InvalidArtifactError("excluded identities must be sorted and unique")
    if set(snapshot.included) & set(excluded_ids):
        raise InvalidArtifactError("included and excluded identities must be disjoint")
    expected = hashlib.sha256(
        _canonical_json(snapshot.canonical(include_id=False))
    ).hexdigest()
    if expected != snapshot.snapshot_id:
        raise ArtifactIntegrityError("snapshot content identity mismatch")


def _validate_hash(value: str, name: str) -> None:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise InvalidArtifactError(f"{name} must be a lowercase SHA-256")
