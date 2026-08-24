from datetime import date
from pathlib import Path

import pytest

from stock_quant.data import ArtifactIntegrityError, InvalidArtifactError
from stock_quant.domain import Exchange, SecurityId
from stock_quant.universe import (
    create_universe_snapshot,
    Exclusion,
    ExclusionCode,
    SecurityExclusions,
    UniverseResult,
    UniverseSnapshot,
    UniverseSnapshotStore,
)


INCLUDED = SecurityId("600000", Exchange.SHANGHAI)
EXCLUDED = SecurityId("000001", Exchange.SHENZHEN)
UPSTREAM_ONE = "a" * 64
UPSTREAM_TWO = "b" * 64
CODE = "c" * 64
CONFIG = "d" * 64


def result(rule_version: str = "universe-v1") -> UniverseResult:
    return UniverseResult(
        date(2020, 1, 7),
        rule_version,
        (INCLUDED,),
        (
            SecurityExclusions(
                EXCLUDED,
                (
                    Exclusion(
                        ExclusionCode.NOT_INDEX_MEMBER,
                        "index_membership",
                        "not a historical constituent",
                        (("index_id", "fixture-index"),),
                    ),
                ),
            ),
        ),
    )


def snapshot(
    upstream: tuple[str, ...] = (UPSTREAM_ONE, UPSTREAM_TWO)
) -> UniverseSnapshot:
    return create_universe_snapshot(
        result(),
        upstream_identities=upstream,
        code_identity=CODE,
        config_identity=CONFIG,
    )


def path(root: Path, snapshot_id: str) -> Path:
    return root / "sha256" / snapshot_id[:2] / f"{snapshot_id}.json"


def test_round_trip_reproducibility_and_full_traceability(tmp_path: Path) -> None:
    first = snapshot((UPSTREAM_TWO, UPSTREAM_ONE))
    second = snapshot((UPSTREAM_ONE, UPSTREAM_TWO))
    store = UniverseSnapshotStore(tmp_path)

    assert first == second
    assert first.upstream_identities == (UPSTREAM_ONE, UPSTREAM_TWO)
    assert store.put(first) == first
    assert store.put(first) == first
    assert store.read(first.snapshot_id) == first
    assert first.code_identity == CODE
    assert first.config_identity == CONFIG
    assert first.rule_version == "universe-v1"


def test_tamper_is_detected_and_never_overwritten(tmp_path: Path) -> None:
    item = snapshot()
    store = UniverseSnapshotStore(tmp_path)
    store.put(item)
    target = path(tmp_path, item.snapshot_id)
    target.write_text("{}")

    with pytest.raises(ArtifactIntegrityError):
        store.read(item.snapshot_id)
    with pytest.raises(ArtifactIntegrityError, match="tamper"):
        store.put(item)
    assert target.read_text() == "{}"


def test_missing_versions_or_trace_identities_are_rejected() -> None:
    with pytest.raises(InvalidArtifactError, match="rule_version"):
        create_universe_snapshot(
            result(""),
            upstream_identities=(UPSTREAM_ONE,),
            code_identity=CODE,
            config_identity=CONFIG,
        )
    with pytest.raises(InvalidArtifactError, match="upstream"):
        create_universe_snapshot(
            result(), upstream_identities=(), code_identity=CODE, config_identity=CONFIG
        )
    with pytest.raises(InvalidArtifactError, match="SHA-256"):
        create_universe_snapshot(
            result(),
            upstream_identities=("../artifact",),
            code_identity=CODE,
            config_identity=CONFIG,
        )


def test_atomic_publish_failure_leaves_no_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    item = snapshot()

    def fail_link(*args: object, **kwargs: object) -> None:
        raise OSError("injected atomic publish failure")

    monkeypatch.setattr("stock_quant.universe.snapshot.os.link", fail_link)
    with pytest.raises(OSError, match="injected"):
        UniverseSnapshotStore(tmp_path).put(item)

    assert not path(tmp_path, item.snapshot_id).exists()
    assert not list(tmp_path.rglob(".snapshot-*"))
