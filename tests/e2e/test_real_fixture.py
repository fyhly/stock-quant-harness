import hashlib
import json
from decimal import Decimal
from pathlib import Path

import pyarrow.parquet as pq  # type: ignore[import-untyped]


ROOT = Path(__file__).parents[1] / "fixtures" / "real" / "v1"


def test_frozen_raw_hash_schema_units_and_offline_reload() -> None:
    manifest = json.loads((ROOT / "manifest.json").read_text())
    assert manifest["fixture_version"] == "real-a-share-v1"
    assert manifest["fqt"] == "0" and manifest["adjustment"] == "unadjusted"
    assert {row["security_id"] for row in manifest["entries"]} == {
        "600000.XSHG",
        "000001.XSHE",
    }
    for entry in manifest["entries"]:
        content = (ROOT / entry["raw_file"]).read_bytes()
        assert hashlib.sha256(content).hexdigest() == entry["sha256"]
        assert entry["url"].startswith("https://") and entry["query"]["fqt"] == "0"
    table = pq.read_table(ROOT / "bars.parquet")
    assert table.num_rows == 968
    assert table.schema.metadata == {
        b"schema_version": b"real-bars-v1",
        b"adjustment": b"unadjusted-fqt-0",
    }
    assert min(table.column("volume_lots").to_pylist()) >= 0


def test_frozen_rows_have_unique_ordered_dates_and_valid_ohlc() -> None:
    rows = pq.read_table(ROOT / "bars.parquet").to_pylist()
    keys = [(row["security_id"], row["trading_day"]) for row in rows]
    assert keys == sorted(set(keys))
    for row in rows:
        prices = [Decimal(row[name]) for name in ("open", "close", "high", "low")]
        assert prices[2] >= max(prices) and prices[3] <= min(prices)
