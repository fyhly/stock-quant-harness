from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
from pathlib import Path

import pytest

from stock_quant.data import (
    ArtifactIntegrityError,
    assess_daily_bars,
    DailyBar,
    DailyBarParquetStore,
    DailyBarSeries,
    InvalidArtifactError,
    LineageRecord,
    LineageStore,
    NormalizedArtifactRef,
    RawArtifactMetadata,
    RawArtifactRef,
    RawArtifactStore,
)
from stock_quant.domain import Exchange, SecurityId, TradingDay


SECURITY = SecurityId("600000", Exchange.SHANGHAI)
CODE_ID = "c" * 64
CONFIG_ID = "d" * 64


def raw_metadata(source: str) -> RawArtifactMetadata:
    return RawArtifactMetadata(
        source=source,
        query={"symbol": "600000.XSHG"},
        fetched_at=datetime(2024, 1, 3, tzinfo=timezone.utc),
        schema_name="fixture-raw",
        schema_version="v1",
    )


def bars() -> DailyBarSeries:
    return DailyBarSeries(
        SECURITY,
        [
            DailyBar(
                SECURITY,
                TradingDay(date(2024, 1, 2)),
                Decimal("10"),
                Decimal("11"),
                Decimal("9"),
                Decimal("10.5"),
                100,
                Decimal("1050"),
            )
        ],
    )


def stores(tmp_path: Path) -> tuple[RawArtifactStore, DailyBarParquetStore, LineageStore]:
    raw_store = RawArtifactStore(tmp_path / "raw")
    normalized_store = DailyBarParquetStore(tmp_path / "normalized")
    lineage_store = LineageStore(
        tmp_path / "lineage",
        raw_store=raw_store,
        normalized_store=normalized_store,
    )
    return raw_store, normalized_store, lineage_store


def put_lineage(
    lineage_store: LineageStore,
    normalized_ref: NormalizedArtifactRef,
    raw_refs: list[RawArtifactRef],
) -> LineageRecord:
    return lineage_store.put(
        normalized_ref,
        raw_refs,
        transform_name="fixture-normalize",
        transform_version="v1",
        code_identity=CODE_ID,
        config_identity=CONFIG_ID,
        quality_report=assess_daily_bars(bars().bars),
    )


def test_full_raw_normalized_quality_lineage_trace(tmp_path: Path) -> None:
    raw_store, normalized_store, lineage_store = stores(tmp_path)
    raw_ref = raw_store.put(b"source bytes", raw_metadata("fixture-one"))
    normalized_ref = normalized_store.put(bars(), raw_ref.artifact_id)

    record = put_lineage(lineage_store, normalized_ref, [raw_ref])

    assert lineage_store.read(record.lineage_id) == record
    assert record.raw_artifact_ids == (raw_ref.artifact_id,)
    assert record.normalized_artifact_id == normalized_ref.artifact_id
    assert record.quality_passed


def test_multi_parent_order_is_deterministic(tmp_path: Path) -> None:
    raw_store, normalized_store, lineage_store = stores(tmp_path)
    first = raw_store.put(b"first", raw_metadata("fixture-one"))
    second = raw_store.put(b"second", raw_metadata("fixture-two"))
    normalized_ref = normalized_store.put(bars(), first.artifact_id)

    forward = put_lineage(lineage_store, normalized_ref, [first, second])
    reverse = put_lineage(lineage_store, normalized_ref, [second, first])

    assert forward == reverse
    assert forward.raw_artifact_ids == tuple(sorted((first.artifact_id, second.artifact_id)))


def test_missing_or_fabricated_raw_parent_is_rejected(tmp_path: Path) -> None:
    raw_store, normalized_store, lineage_store = stores(tmp_path)
    raw_ref = raw_store.put(b"real", raw_metadata("fixture-one"))
    normalized_ref = normalized_store.put(bars(), raw_ref.artifact_id)
    fabricated = RawArtifactRef("f" * 64, "e" * 64, raw_metadata("fabricated"))

    with pytest.raises(InvalidArtifactError, match="direct Raw parent"):
        put_lineage(lineage_store, normalized_ref, [fabricated])
    with pytest.raises(ArtifactIntegrityError, match="missing"):
        put_lineage(lineage_store, normalized_ref, [raw_ref, fabricated])


def test_tampered_raw_or_normalized_parent_is_rejected(tmp_path: Path) -> None:
    raw_store, normalized_store, lineage_store = stores(tmp_path)
    raw_ref = raw_store.put(b"real", raw_metadata("fixture-one"))
    normalized_ref = normalized_store.put(bars(), raw_ref.artifact_id)
    raw_payload = (
        raw_store.root
        / "sha256"
        / raw_ref.artifact_id[:2]
        / raw_ref.artifact_id
        / "payload.bin"
    )
    raw_payload.write_bytes(b"tampered")
    with pytest.raises(ArtifactIntegrityError, match="payload"):
        put_lineage(lineage_store, normalized_ref, [raw_ref])

    raw_payload.write_bytes(b"real")
    parquet = next(normalized_store.root.rglob("data.parquet"))
    parquet.write_bytes(b"PAR1tampered")
    with pytest.raises(ArtifactIntegrityError, match="content hash"):
        put_lineage(lineage_store, normalized_ref, [raw_ref])


def test_lineage_tamper_and_identity_validation(tmp_path: Path) -> None:
    raw_store, normalized_store, lineage_store = stores(tmp_path)
    raw_ref = raw_store.put(b"real", raw_metadata("fixture-one"))
    normalized_ref = normalized_store.put(bars(), raw_ref.artifact_id)
    record = put_lineage(lineage_store, normalized_ref, [raw_ref])
    path = (
        lineage_store.root
        / "sha256"
        / record.lineage_id[:2]
        / f"{record.lineage_id}.json"
    )
    path.write_text("{}")

    with pytest.raises(ArtifactIntegrityError, match="identity"):
        lineage_store.read(record.lineage_id)
    with pytest.raises(ArtifactIntegrityError, match="tamper"):
        put_lineage(lineage_store, normalized_ref, [raw_ref])


def test_raw_reference_content_hash_is_verified(tmp_path: Path) -> None:
    raw_store, normalized_store, lineage_store = stores(tmp_path)
    raw_ref = raw_store.put(b"real", raw_metadata("fixture-one"))
    normalized_ref = normalized_store.put(bars(), raw_ref.artifact_id)
    false_ref = RawArtifactRef(
        raw_ref.artifact_id,
        hashlib.sha256(b"false").hexdigest(),
        raw_ref.metadata,
    )
    with pytest.raises(ArtifactIntegrityError, match="reference content hash"):
        put_lineage(lineage_store, normalized_ref, [false_ref])
