from datetime import date
from decimal import Decimal
from pathlib import Path

import pyarrow.parquet as pq  # type: ignore[import-untyped]
import pytest

from stock_quant.data import (
    ArtifactIntegrityError,
    DailyBar,
    DailyBarParquetStore,
    DailyBarSeries,
    InvalidArtifactError,
)
from stock_quant.domain import Exchange, SecurityId, TradingDay


RAW_ID = "a" * 64
SECURITY = SecurityId("600000", Exchange.SHANGHAI)


def series(*days: int) -> DailyBarSeries:
    return DailyBarSeries(
        SECURITY,
        [
            DailyBar(
                security_id=SECURITY,
                trading_day=TradingDay(date(2024, 1, day)),
                open=Decimal("10.0000000001"),
                high=Decimal("11"),
                low=Decimal("9"),
                close=Decimal("10.5"),
                volume=1000 + day,
                amount=Decimal("10500.1234"),
            )
            for day in days
        ],
    )


def target(root: Path, artifact_id: str) -> Path:
    return (
        root
        / "schema=daily-bar-v1"
        / "exchange=XSHG"
        / "security=600000"
        / "year=2024"
        / f"artifact={artifact_id}"
    )


def test_true_parquet_round_trip_and_fixed_partition(tmp_path: Path) -> None:
    store = DailyBarParquetStore(tmp_path)
    original = series(2, 3)
    ref = store.put(original, RAW_ID)

    artifact_path = target(tmp_path, ref.artifact_id)
    assert artifact_path.joinpath("data.parquet").read_bytes()[:4] == b"PAR1"
    assert pq.read_metadata(artifact_path / "data.parquet").num_rows == 2
    assert store.read(ref) == original


def test_deterministic_bytes_order_and_idempotence(tmp_path: Path) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first = DailyBarParquetStore(first_root).put(series(2, 3), RAW_ID)
    second = DailyBarParquetStore(second_root).put(series(2, 3), RAW_ID)
    repeated = DailyBarParquetStore(first_root).put(series(2, 3), RAW_ID)

    assert first == second == repeated
    assert target(first_root, first.artifact_id).joinpath(
        "data.parquet"
    ).read_bytes() == target(second_root, second.artifact_id).joinpath(
        "data.parquet"
    ).read_bytes()


def test_parquet_tamper_is_detected_and_not_overwritten(tmp_path: Path) -> None:
    store = DailyBarParquetStore(tmp_path)
    ref = store.put(series(2), RAW_ID)
    parquet_path = target(tmp_path, ref.artifact_id) / "data.parquet"
    parquet_path.write_bytes(b"PAR1tampered")

    with pytest.raises(ArtifactIntegrityError, match="content hash"):
        store.read(ref)
    with pytest.raises(ArtifactIntegrityError, match="tamper"):
        store.put(series(2), RAW_ID)
    assert parquet_path.read_bytes() == b"PAR1tampered"


def test_manifest_tamper_is_detected(tmp_path: Path) -> None:
    store = DailyBarParquetStore(tmp_path)
    ref = store.put(series(2), RAW_ID)
    (target(tmp_path, ref.artifact_id) / "manifest.json").write_text("{}")

    with pytest.raises(ArtifactIntegrityError, match="identity"):
        store.read(ref)


def test_partition_and_parent_validation_fail_closed(tmp_path: Path) -> None:
    store = DailyBarParquetStore(tmp_path)
    with pytest.raises(InvalidArtifactError, match="SHA-256"):
        store.put(series(2), "../../raw")
    with pytest.raises(InvalidArtifactError, match="one year"):
        cross_year = DailyBarSeries(
            SECURITY,
            [series(2).bars[0], series(3).bars[0].__class__(
                security_id=SECURITY,
                trading_day=TradingDay(date(2025, 1, 3)),
                open=Decimal("10"),
                high=Decimal("11"),
                low=Decimal("9"),
                close=Decimal("10"),
                volume=1,
                amount=Decimal("10"),
            )],
        )
        store.put(cross_year, RAW_ID)


def test_lossy_scale_is_rejected(tmp_path: Path) -> None:
    too_precise = DailyBar(
        security_id=SECURITY,
        trading_day=TradingDay(date(2024, 1, 2)),
        open=Decimal("10.00000000001"),
        high=Decimal("11"),
        low=Decimal("9"),
        close=Decimal("10"),
        volume=1,
        amount=Decimal("10"),
    )
    with pytest.raises(InvalidArtifactError, match="scale"):
        DailyBarParquetStore(tmp_path).put(
            DailyBarSeries(SECURITY, [too_precise]), RAW_ID
        )


def test_atomic_write_failure_leaves_no_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_write(*args: object, **kwargs: object) -> None:
        raise OSError("injected write failure")

    monkeypatch.setattr("stock_quant.data.storage.pq.write_table", fail_write)
    with pytest.raises(OSError, match="injected"):
        DailyBarParquetStore(tmp_path).put(series(2), RAW_ID)

    assert not list(tmp_path.rglob("artifact=*"))
    assert not list(tmp_path.rglob(".normalized-*"))
