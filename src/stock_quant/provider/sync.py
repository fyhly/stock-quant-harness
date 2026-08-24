"""Explicit staged incremental sync with immutable deterministic manifests."""

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Callable, Generic, Optional, TypeVar

from stock_quant.data import RawArtifactRef
from stock_quant.provider.api import TerminalProviderError


T = TypeVar("T")


@dataclass(frozen=True)
class SyncPlan:
    dataset: str
    previous_watermark: Optional[str]
    target_watermark: str


@dataclass(frozen=True)
class SyncManifest:
    dataset: str
    watermark: str
    raw_identity: str
    normalized_identity: str
    manifest_identity: str


class IncrementalSync(Generic[T]):
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        plan: SyncPlan,
        *,
        credential: str,
        acquire: Callable[[str], tuple[RawArtifactRef, T]],
        validate: Callable[[T], None],
        publish: Callable[[T], str],
    ) -> SyncManifest:
        if not credential:
            raise TerminalProviderError("missing runtime credential")
        existing = self._read(plan.dataset, plan.target_watermark)
        if existing is not None:
            return existing
        raw, staged = acquire(credential)
        validate(staged)
        normalized_identity = publish(staged)
        payload = {
            "dataset": plan.dataset,
            "normalized_identity": normalized_identity,
            "raw_identity": raw.artifact_id,
            "watermark": plan.target_watermark,
        }
        identity = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        manifest = SyncManifest(
            plan.dataset,
            plan.target_watermark,
            raw.artifact_id,
            normalized_identity,
            identity,
        )
        self._write(manifest, payload)
        return manifest

    def _path(self, dataset: str, watermark: str) -> Path:
        if (
            not dataset.replace("-", "").isalnum()
            or not watermark.replace("-", "").isalnum()
        ):
            raise TerminalProviderError("invalid sync path identity")
        return self.root / dataset / f"{watermark}.json"

    def _read(self, dataset: str, watermark: str) -> Optional[SyncManifest]:
        path = self._path(dataset, watermark)
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        payload = {
            key: data[key]
            for key in ("dataset", "normalized_identity", "raw_identity", "watermark")
        }
        identity = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        if data.get("manifest_identity") != identity:
            raise TerminalProviderError("sync manifest tamper")
        return SyncManifest(
            data["dataset"],
            data["watermark"],
            data["raw_identity"],
            data["normalized_identity"],
            identity,
        )

    def _write(self, manifest: SyncManifest, payload: dict[str, str]) -> None:
        path = self._path(manifest.dataset, manifest.watermark)
        path.parent.mkdir(parents=True, exist_ok=True)
        document = dict(payload, manifest_identity=manifest.manifest_identity)
        fd, name = tempfile.mkstemp(prefix=".sync-", dir=path.parent)
        try:
            with os.fdopen(fd, "w") as stream:
                json.dump(document, stream, sort_keys=True, separators=(",", ":"))
            try:
                os.link(name, path)
            except FileExistsError:
                existing = self._read(manifest.dataset, manifest.watermark)
                if existing != manifest:
                    raise TerminalProviderError("sync manifest collision")
        finally:
            if os.path.exists(name):
                os.unlink(name)
