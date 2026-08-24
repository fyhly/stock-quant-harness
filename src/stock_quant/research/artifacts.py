"""Atomic append-only run artifact store with stable schemas."""

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Mapping, Tuple
import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]
from stock_quant.backtest import BacktestResult
from stock_quant.research.run_id import RunId


class RunArtifactError(RuntimeError):
    pass


@dataclass(frozen=True)
class RunArtifacts:
    run_id: RunId
    files: Tuple[Tuple[str, str], ...]


class RunStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def publish(
        self,
        run_id: RunId,
        result: BacktestResult,
        *,
        metrics: Mapping[str, str],
        failures: Tuple[str, ...],
        fail_after_stage: bool = False,
    ) -> RunArtifacts:
        target = self.root / run_id.value
        if target.exists():
            raise RunArtifactError("run artifacts already exist")
        temp = Path(tempfile.mkdtemp(prefix=".run-", dir=self.root))
        try:
            trades = [
                {
                    "order_id": fill.order_id,
                    "security_id": str(fill.security_id),
                    "day": fill.trading_day.value.isoformat(),
                    "side": fill.side.value,
                    "quantity": fill.quantity,
                    "price": str(fill.price),
                    "cost": str(fill.costs.total),
                }
                for fill in result.fills
            ]
            holdings = [
                {
                    "day": item.trading_day.value.isoformat(),
                    "cash": str(item.cash),
                    "positions_json": json.dumps(
                        [[str(s), q, str(c)] for s, q, c in item.positions],
                        separators=(",", ":"),
                    ),
                }
                for item in result.holdings
            ]
            equity = [
                {"day": item.trading_day.value.isoformat(), "equity": str(item.equity)}
                for item in result.equity
            ]
            self._parquet(
                temp / "trades.parquet",
                trades,
                pa.schema(
                    [
                        ("order_id", pa.string()),
                        ("security_id", pa.string()),
                        ("day", pa.string()),
                        ("side", pa.string()),
                        ("quantity", pa.int64()),
                        ("price", pa.string()),
                        ("cost", pa.string()),
                    ]
                ),
            )
            self._parquet(
                temp / "holdings.parquet",
                holdings,
                pa.schema(
                    [
                        ("day", pa.string()),
                        ("cash", pa.string()),
                        ("positions_json", pa.string()),
                    ]
                ),
            )
            self._parquet(
                temp / "equity.parquet",
                equity,
                pa.schema([("day", pa.string()), ("equity", pa.string())]),
            )
            (temp / "metrics.json").write_bytes(_json(dict(metrics)))
            (temp / "failures.json").write_bytes(_json({"failures": list(failures)}))
            if fail_after_stage:
                raise RunArtifactError("injected staged failure")
            files = tuple(
                sorted(
                    (path.name, hashlib.sha256(path.read_bytes()).hexdigest())
                    for path in temp.iterdir()
                )
            )
            (temp / "artifact-manifest.json").write_bytes(
                _json(
                    {
                        "run_id": run_id.value,
                        "schema": "research-artifacts-v1",
                        "files": files,
                        "backtest_fingerprint": result.fingerprint,
                    }
                )
            )
            os.rename(temp, target)
            return self.load(run_id)
        finally:
            if temp.exists():
                shutil.rmtree(temp)

    def load(self, run_id: RunId) -> RunArtifacts:
        target = self.root / run_id.value
        try:
            manifest = json.loads((target / "artifact-manifest.json").read_text())
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            raise RunArtifactError("artifact manifest missing or corrupt") from exc
        if (
            manifest.get("run_id") != run_id.value
            or manifest.get("schema") != "research-artifacts-v1"
        ):
            raise RunArtifactError("artifact manifest identity mismatch")
        files = tuple((str(name), str(digest)) for name, digest in manifest["files"])
        for name, digest in files:
            if hashlib.sha256((target / name).read_bytes()).hexdigest() != digest:
                raise RunArtifactError(f"artifact tamper: {name}")
        return RunArtifacts(run_id, files)

    @staticmethod
    def _parquet(path: Path, rows: Any, schema: Any) -> None:
        pq.write_table(
            pa.Table.from_pylist(rows, schema=schema),
            path,
            compression="NONE",
            version="2.6",
        )


def _json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
