"""Bounded deterministic cross-sectional batch execution."""

from dataclasses import dataclass
from datetime import date
import hashlib
import json
from typing import Callable, Iterable, Tuple

from stock_quant.domain import SecurityId


@dataclass(frozen=True, order=True)
class MarketWorkItem:
    research_date: date
    security_id: SecurityId
    input_identity: str

    @property
    def item_id(self) -> str:
        raw = (
            f"{self.research_date.isoformat()}|{self.security_id}|{self.input_identity}"
        )
        return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True)
class MarketItemRecord:
    item: MarketWorkItem
    item_id: str
    succeeded: bool
    output: str
    failure_type: str
    failure_message: str


@dataclass(frozen=True)
class MarketBatchResult:
    manifest_identity: str
    partition_size: int
    total: int
    succeeded: int
    failed: int
    records: Tuple[MarketItemRecord, ...]


def run_cross_sectional_batch(
    items: Iterable[MarketWorkItem],
    callback: Callable[[MarketWorkItem], str],
    *,
    partition_size: int,
) -> MarketBatchResult:
    if partition_size <= 0:
        raise ValueError("partition_size must be positive")
    ordered = tuple(sorted(items))
    if len({item.item_id for item in ordered}) != len(ordered):
        raise ValueError("duplicate batch work item")
    manifest = hashlib.sha256(
        json.dumps(
            {
                "items": [item.item_id for item in ordered],
                "partition_size": partition_size,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    records = []
    for start in range(0, len(ordered), partition_size):
        for item in ordered[start : start + partition_size]:
            try:
                output = callback(item)
                records.append(
                    MarketItemRecord(item, item.item_id, True, output, "", "")
                )
            except Exception as exc:
                records.append(
                    MarketItemRecord(
                        item, item.item_id, False, "", type(exc).__name__, str(exc)
                    )
                )
    succeeded = sum(record.succeeded for record in records)
    return MarketBatchResult(
        manifest,
        partition_size,
        len(records),
        succeeded,
        len(records) - succeeded,
        tuple(records),
    )
