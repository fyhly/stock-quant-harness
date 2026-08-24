"""Idempotent staged orchestration over explicit Provider sync boundaries."""

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Callable, Iterable, Tuple

from stock_quant.provider.sync import SyncManifest


class DailyUpdateError(RuntimeError):
    pass


@dataclass(frozen=True)
class DailyDataUpdate:
    run_identity: str
    watermark: str
    data_identity: str
    manifests: Tuple[SyncManifest, ...]
    recovery_state: str


def run_daily_update(
    root: Path,
    *,
    run_identity: str,
    watermark: str,
    dataset_updates: Iterable[tuple[str, Callable[[], SyncManifest]]],
) -> DailyDataUpdate:
    target = Path(root) / f"{run_identity}.json"
    if target.exists():
        return _read(target)
    updates = tuple(sorted(dataset_updates, key=lambda item: item[0]))
    if len(run_identity) != 64 or not watermark or not updates:
        raise DailyUpdateError("invalid daily update identity or plan")
    manifests = []
    try:
        for dataset, callback in updates:
            manifest = callback()
            if manifest.dataset != dataset or manifest.watermark != watermark:
                raise DailyUpdateError(
                    "provider sync manifest does not match daily plan"
                )
            manifests.append(manifest)
    except Exception as exc:
        raise DailyUpdateError(
            f"daily update staged failure after {len(manifests)} datasets"
        ) from exc
    data_identity = hashlib.sha256(
        "|".join(item.manifest_identity for item in manifests).encode()
    ).hexdigest()
    result = DailyDataUpdate(
        run_identity, watermark, data_identity, tuple(manifests), "PUBLISHED"
    )
    raw = _json(result)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".daily-update-", dir=target.parent)
    temp = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temp, target)
        except FileExistsError:
            if target.read_bytes() != raw:
                raise DailyUpdateError("daily update collision; old good data retained")
    finally:
        temp.unlink(missing_ok=True)
    return _read(target)


def _json(result: DailyDataUpdate) -> bytes:
    return json.dumps(
        {
            "run_identity": result.run_identity,
            "watermark": result.watermark,
            "data_identity": result.data_identity,
            "manifests": [item.__dict__ for item in result.manifests],
            "recovery_state": result.recovery_state,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def _read(path: Path) -> DailyDataUpdate:
    try:
        data = json.loads(path.read_text())
        result = DailyDataUpdate(
            data["run_identity"],
            data["watermark"],
            data["data_identity"],
            tuple(SyncManifest(**item) for item in data["manifests"]),
            data["recovery_state"],
        )
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise DailyUpdateError("daily update state missing or corrupt") from exc
    expected = hashlib.sha256(
        "|".join(item.manifest_identity for item in result.manifests).encode()
    ).hexdigest()
    if result.data_identity != expected or path.read_bytes() != _json(result):
        raise DailyUpdateError("daily update state tampered")
    return result
