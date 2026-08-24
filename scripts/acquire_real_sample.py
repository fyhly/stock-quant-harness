"""One-time HTTPS acquisition of frozen, unadjusted Eastmoney daily bars."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.parse
import urllib.request

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]


ROOT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "real" / "v1"
SECURITIES = {"600000.XSHG": "1.600000", "000001.XSHE": "0.000001"}


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    entries = []
    normalized = []
    for canonical, secid in SECURITIES.items():
        params = {
            "secid": secid,
            "klt": "101",
            "fqt": "0",
            "beg": "20230101",
            "end": "20241231",
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        }
        url = (
            "https://push2his.eastmoney.com/api/qt/stock/kline/get?"
            + urllib.parse.urlencode(params)
        )
        request = urllib.request.Request(
            url, headers={"User-Agent": "stock-quant-harness/real-sample-v1"}
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            content = response.read()
        path = ROOT / f"{canonical}.json"
        path.write_bytes(content)
        fetched = datetime.now(timezone.utc).isoformat(timespec="microseconds")
        entries.append(
            {
                "security_id": canonical,
                "url": url,
                "query": params,
                "fetched_at": fetched,
                "sha256": hashlib.sha256(content).hexdigest(),
                "schema": "eastmoney-kline-f51-f61-v1",
                "raw_file": path.name,
            }
        )
        payload = json.loads(content)
        if payload.get("rc") != 0 or payload.get("data") is None:
            raise RuntimeError("Eastmoney returned an error")
        for raw in payload["data"]["klines"]:
            values = raw.split(",")
            if len(values) != 11:
                raise RuntimeError("Eastmoney schema drift")
            normalized.append(
                {
                    "security_id": canonical,
                    "trading_day": values[0],
                    "open": values[1],
                    "close": values[2],
                    "high": values[3],
                    "low": values[4],
                    "volume_lots": int(values[5]),
                    "amount_yuan": values[6],
                    "source_sha256": hashlib.sha256(content).hexdigest(),
                }
            )
    normalized.sort(key=lambda row: (row["security_id"], row["trading_day"]))
    schema = pa.schema(
        [
            ("security_id", pa.string()),
            ("trading_day", pa.string()),
            ("open", pa.string()),
            ("close", pa.string()),
            ("high", pa.string()),
            ("low", pa.string()),
            ("volume_lots", pa.int64()),
            ("amount_yuan", pa.string()),
            ("source_sha256", pa.string()),
        ],
        metadata={
            b"schema_version": b"real-bars-v1",
            b"adjustment": b"unadjusted-fqt-0",
        },
    )
    pq.write_table(
        pa.Table.from_pylist(normalized, schema=schema),
        ROOT / "bars.parquet",
        compression="NONE",
        version="2.6",
    )
    manifest = {
        "fixture_version": "real-a-share-v1",
        "source": "Eastmoney public HTTPS kline",
        "adjustment": "unadjusted",
        "fqt": "0",
        "entries": entries,
        "normalized_file": "bars.parquet",
        "normalized_sha256": hashlib.sha256(
            (ROOT / "bars.parquet").read_bytes()
        ).hexdigest(),
    }
    (ROOT / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
