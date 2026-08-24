from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

import pytest

from stock_quant.data import RawArtifactMetadata, RawArtifactRef, RawArtifactStore
from stock_quant.provider import IncrementalSync, SyncPlan


def test_repeat_sync_is_idempotent_and_manifest_has_no_secret(tmp_path: Path) -> None:
    raw = RawArtifactStore(tmp_path / "raw").put(
        b"exact",
        RawArtifactMetadata("source", {}, datetime.now(timezone.utc), "schema", "v1"),
    )
    calls: List[str] = []
    sync = IncrementalSync[str](tmp_path / "sync")

    def acquire(secret: str) -> Tuple[RawArtifactRef, str]:
        calls.append(secret)
        return raw, "staged"

    plan = SyncPlan("daily", None, "2024-01-02")
    first = sync.run(
        plan,
        credential="top-secret",
        acquire=acquire,
        validate=lambda value: None,
        publish=lambda value: "normalized",
    )
    second = sync.run(
        plan,
        credential="top-secret",
        acquire=acquire,
        validate=lambda value: None,
        publish=lambda value: "normalized",
    )
    assert first == second and calls == ["top-secret"]
    assert b"top-secret" not in next((tmp_path / "sync").rglob("*.json")).read_bytes()


def test_validation_failure_does_not_publish_or_replace_old(tmp_path: Path) -> None:
    raw = RawArtifactStore(tmp_path / "raw").put(
        b"exact",
        RawArtifactMetadata("source", {}, datetime.now(timezone.utc), "schema", "v1"),
    )
    published: List[str] = []

    def invalid(value: str) -> None:
        raise ValueError("schema")

    def publish(value: str) -> str:
        published.append(value)
        return "new"

    with pytest.raises(ValueError, match="schema"):
        IncrementalSync[str](tmp_path / "sync").run(
            SyncPlan("daily", "old", "new"),
            credential="x",
            acquire=lambda secret: (raw, "bad"),
            validate=invalid,
            publish=publish,
        )
    assert published == [] and not tuple((tmp_path / "sync").rglob("*.json"))
