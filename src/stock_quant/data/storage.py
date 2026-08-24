"""Deterministic local Parquet persistence for normalized daily bars."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any, cast, Dict, Mapping, Tuple

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]

from stock_quant.data.bars import DAILY_BAR_SCHEMA_VERSION, DailyBar, DailyBarSeries
from stock_quant.data.raw import ArtifactIntegrityError, InvalidArtifactError
from stock_quant.domain import Exchange, SecurityId, TradingDay


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PRICE_TYPE = pa.decimal128(38, 10)
_AMOUNT_TYPE = pa.decimal128(38, 4)
_PARQUET_SCHEMA = pa.schema(
    [
        pa.field("security_code", pa.string(), nullable=False),
        pa.field("exchange", pa.string(), nullable=False),
        pa.field("trading_date", pa.date32(), nullable=False),
        pa.field("open", _PRICE_TYPE, nullable=False),
        pa.field("high", _PRICE_TYPE, nullable=False),
        pa.field("low", _PRICE_TYPE, nullable=False),
        pa.field("close", _PRICE_TYPE, nullable=False),
        pa.field("volume", pa.int64(), nullable=False),
        pa.field("amount", _AMOUNT_TYPE, nullable=False),
    ],
    metadata={
        b"stock_quant.format": b"daily-bars-parquet-v1",
        b"stock_quant.schema": DAILY_BAR_SCHEMA_VERSION.encode("ascii"),
        b"stock_quant.adjustment": b"unadjusted",
    },
)


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


@dataclass(frozen=True)
class NormalizedArtifactRef:
    artifact_id: str
    content_hash: str
    source_raw_artifact_id: str
    security_id: SecurityId
    year: int
    row_count: int


class DailyBarParquetStore:
    """Atomic, no-overwrite local store with a fixed partition convention."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        if not self.root.is_dir():
            raise InvalidArtifactError("normalized store root must be a directory")

    def put(
        self, series: DailyBarSeries, source_raw_artifact_id: str
    ) -> NormalizedArtifactRef:
        if not isinstance(series, DailyBarSeries):
            raise TypeError("series must be a DailyBarSeries")
        self._validate_hash(source_raw_artifact_id, "source_raw_artifact_id")
        if not series.bars:
            raise InvalidArtifactError("cannot publish an empty daily-bar partition")
        years = {bar.trading_day.value.year for bar in series.bars}
        if len(years) != 1:
            raise InvalidArtifactError("one artifact must contain exactly one year partition")
        year = next(iter(years))

        table = self._table(series)
        partition = self._partition(series.security_id, year)
        partition_key = partition.as_posix()
        logical = {
            "format": "daily-bars-parquet-v1",
            "partition": partition_key,
            "rows": self._logical_rows(series),
            "source_raw_artifact_id": source_raw_artifact_id,
        }
        logical_hash = hashlib.sha256(_canonical_json(logical)).hexdigest()

        partition_root = self.root / partition
        partition_root.mkdir(parents=True, exist_ok=True)
        temp_path = Path(tempfile.mkdtemp(prefix=".normalized-", dir=partition_root))
        try:
            parquet_path = temp_path / "data.parquet"
            pq.write_table(
                table,
                parquet_path,
                compression="NONE",
                version="2.6",
                data_page_version="1.0",
                use_dictionary=False,
                write_statistics=True,
                row_group_size=len(series.bars),
            )
            parquet_bytes = parquet_path.read_bytes()
            content_hash = hashlib.sha256(parquet_bytes).hexdigest()
            manifest = {
                "content_hash": content_hash,
                "format": "daily-bars-parquet-v1",
                "logical_hash": logical_hash,
                "partition": partition_key,
                "row_count": len(series.bars),
                "schema_version": DAILY_BAR_SCHEMA_VERSION,
                "source_raw_artifact_id": source_raw_artifact_id,
            }
            artifact_id = hashlib.sha256(_canonical_json(manifest)).hexdigest()
            manifest["artifact_id"] = artifact_id
            (temp_path / "manifest.json").write_bytes(_canonical_json(manifest))
            target = partition_root / f"artifact={artifact_id}"
            ref = NormalizedArtifactRef(
                artifact_id,
                content_hash,
                source_raw_artifact_id,
                series.security_id,
                year,
                len(series.bars),
            )
            if target.exists():
                self._verify_files(target, manifest)
                return ref
            try:
                os.rename(temp_path, target)
            except OSError:
                if not target.exists():
                    raise
                self._verify_files(target, manifest)
            return ref
        finally:
            if temp_path.exists():
                shutil.rmtree(temp_path)

    def read(self, ref: NormalizedArtifactRef) -> DailyBarSeries:
        self._validate_ref(ref)
        partition = self._partition(ref.security_id, ref.year)
        target = self.root / partition / f"artifact={ref.artifact_id}"
        manifest = self._read_and_verify_manifest(target, ref.artifact_id)
        if manifest["partition"] != partition.as_posix():
            raise ArtifactIntegrityError("normalized partition mismatch")
        if manifest["source_raw_artifact_id"] != ref.source_raw_artifact_id:
            raise ArtifactIntegrityError("normalized Raw parent mismatch")
        if manifest["content_hash"] != ref.content_hash:
            raise ArtifactIntegrityError("normalized content reference mismatch")
        parquet_path = target / "data.parquet"
        if hashlib.sha256(parquet_path.read_bytes()).hexdigest() != ref.content_hash:
            raise ArtifactIntegrityError("normalized Parquet content hash mismatch")
        table = pq.ParquetFile(parquet_path).read()
        if not table.schema.equals(_PARQUET_SCHEMA, check_metadata=True):
            raise ArtifactIntegrityError("normalized Parquet schema mismatch")
        bars = tuple(self._bar_from_row(row) for row in table.to_pylist())
        if len(bars) != ref.row_count or manifest["row_count"] != ref.row_count:
            raise ArtifactIntegrityError("normalized row count mismatch")
        return DailyBarSeries(ref.security_id, bars)

    @staticmethod
    def _table(series: DailyBarSeries) -> pa.Table:
        rows = []
        for bar in series.bars:
            for name, value, scale in (
                ("open", bar.open, 10),
                ("high", bar.high, 10),
                ("low", bar.low, 10),
                ("close", bar.close, 10),
                ("amount", bar.amount, 4),
            ):
                exponent = value.as_tuple().exponent
                if not isinstance(exponent, int) or exponent < -scale:
                    raise InvalidArtifactError(
                        f"{name} exceeds fixed Parquet scale {scale}"
                    )
            if not -(2**63) <= bar.volume < 2**63:
                raise InvalidArtifactError("volume exceeds Parquet int64 range")
            rows.append(
                {
                    "security_code": bar.security_id.code,
                    "exchange": bar.security_id.exchange.value,
                    "trading_date": bar.trading_day.value,
                    "open": bar.open,
                    "high": bar.high,
                    "low": bar.low,
                    "close": bar.close,
                    "volume": bar.volume,
                    "amount": bar.amount,
                }
            )
        try:
            return pa.Table.from_pylist(rows, schema=_PARQUET_SCHEMA)
        except (pa.ArrowInvalid, pa.ArrowTypeError) as exc:
            raise InvalidArtifactError("bar values do not fit fixed Parquet schema") from exc

    @staticmethod
    def _logical_rows(series: DailyBarSeries) -> Tuple[Dict[str, Any], ...]:
        return tuple(
            {
                "amount": str(bar.amount),
                "close": str(bar.close),
                "date": bar.trading_day.value.isoformat(),
                "high": str(bar.high),
                "low": str(bar.low),
                "open": str(bar.open),
                "volume": bar.volume,
            }
            for bar in series.bars
        )

    @staticmethod
    def _partition(security_id: SecurityId, year: int) -> Path:
        if not 1900 <= year <= 9999:
            raise InvalidArtifactError("partition year is out of range")
        return Path(
            f"schema={DAILY_BAR_SCHEMA_VERSION}/exchange={security_id.exchange.value}/"
            f"security={security_id.code}/year={year:04d}"
        )

    @staticmethod
    def _bar_from_row(row: Mapping[str, Any]) -> DailyBar:
        security_id = SecurityId(
            str(row["security_code"]), Exchange(str(row["exchange"]))
        )
        trading_date = row["trading_date"]
        if type(trading_date) is not date:
            raise ArtifactIntegrityError("invalid Parquet trading_date")
        return DailyBar(
            security_id=security_id,
            trading_day=TradingDay(trading_date),
            open=Decimal(row["open"]),
            high=Decimal(row["high"]),
            low=Decimal(row["low"]),
            close=Decimal(row["close"]),
            volume=int(row["volume"]),
            amount=Decimal(row["amount"]),
        )

    @staticmethod
    def _validate_hash(value: str, name: str) -> None:
        if not isinstance(value, str) or not _SHA256.fullmatch(value):
            raise InvalidArtifactError(f"{name} must be a lowercase SHA-256")

    def _validate_ref(self, ref: NormalizedArtifactRef) -> None:
        if not isinstance(ref, NormalizedArtifactRef):
            raise TypeError("ref must be a NormalizedArtifactRef")
        self._validate_hash(ref.artifact_id, "artifact_id")
        self._validate_hash(ref.content_hash, "content_hash")
        self._validate_hash(ref.source_raw_artifact_id, "source_raw_artifact_id")

    def _read_and_verify_manifest(
        self, target: Path, artifact_id: str
    ) -> Dict[str, Any]:
        try:
            manifest = json.loads((target / "manifest.json").read_text("utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            raise ArtifactIntegrityError("normalized manifest missing or unreadable") from exc
        claimed = manifest.pop("artifact_id", None)
        if claimed != artifact_id:
            raise ArtifactIntegrityError("normalized manifest identity mismatch")
        if hashlib.sha256(_canonical_json(manifest)).hexdigest() != artifact_id:
            raise ArtifactIntegrityError("normalized manifest hash mismatch")
        manifest["artifact_id"] = claimed
        return cast(Dict[str, Any], manifest)

    def _verify_files(self, target: Path, expected_manifest: Mapping[str, Any]) -> None:
        actual = self._read_and_verify_manifest(target, str(expected_manifest["artifact_id"]))
        if _canonical_json(actual) != _canonical_json(expected_manifest):
            raise ArtifactIntegrityError("normalized artifact collision or manifest tamper")
        parquet_path = target / "data.parquet"
        try:
            content_hash = hashlib.sha256(parquet_path.read_bytes()).hexdigest()
        except FileNotFoundError as exc:
            raise ArtifactIntegrityError("normalized Parquet file is missing") from exc
        if content_hash != expected_manifest["content_hash"]:
            raise ArtifactIntegrityError("normalized artifact collision or Parquet tamper")
