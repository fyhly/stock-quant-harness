"""Ordered isolated fit, select, freeze and OOS orchestration."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Callable, Mapping, Optional, Tuple, TypeVar

from stock_quant.oos.oos_runner import OOSContext, OOSRecord, run_oos
from stock_quant.oos.train import FittedArtifact, TrainContext, TrainRecord, run_train
from stock_quant.oos.validation import (
    FrozenSelection,
    ParameterCandidate,
    ValidationContext,
    run_validation,
)
from stock_quant.oos.windows import OOSWindowSet


T = TypeVar("T")


@dataclass(frozen=True)
class WalkForwardWindowRecord:
    window_identity: str
    train: TrainRecord
    selection: Optional[FrozenSelection]
    oos: Optional[OOSRecord]
    succeeded: bool
    failure_stage: str
    failure_message: str


@dataclass(frozen=True)
class WalkForwardResult:
    records: Tuple[WalkForwardWindowRecord, ...]
    total: int
    succeeded: int
    failed: int


def run_walk_forward(
    windows: Tuple[OOSWindowSet, ...],
    data: Mapping[date, T],
    candidates: Tuple[ParameterCandidate, ...],
    fit: Callable[[TrainContext[T]], Tuple[bytes, bytes]],
    validate: Callable[[ValidationContext[T], ParameterCandidate], Decimal],
    execute: Callable[[OOSContext[T], bytes], bytes],
) -> WalkForwardResult:
    ordered = tuple(sorted(windows, key=lambda item: item.oos.start))
    if ordered != windows or len({item.identity for item in ordered}) != len(ordered):
        raise ValueError("walk-forward windows must be ordered and unique")
    for previous, current in zip(ordered, ordered[1:]):
        if previous.oos.end > current.oos.start:
            raise ValueError("walk-forward OOS windows cannot overlap")
    records = []
    for window in ordered:
        trained = run_train(window, data, fit)
        if not trained.succeeded:
            records.append(
                WalkForwardWindowRecord(
                    window.identity,
                    trained,
                    None,
                    None,
                    False,
                    "TRAIN",
                    trained.failure_message,
                )
            )
            continue
        assert isinstance(trained.fitted, FittedArtifact)
        try:
            selection = run_validation(
                window, data, trained.fitted, candidates, validate
            )
        except Exception as exc:
            records.append(
                WalkForwardWindowRecord(
                    window.identity, trained, None, None, False, "VALIDATION", str(exc)
                )
            )
            continue
        oos = run_oos(window, data, selection, execute)
        records.append(
            WalkForwardWindowRecord(
                window.identity,
                trained,
                selection,
                oos,
                oos.succeeded,
                "" if oos.succeeded else "OOS",
                oos.failure_message,
            )
        )
    succeeded = sum(record.succeeded for record in records)
    return WalkForwardResult(
        tuple(records), len(records), succeeded, len(records) - succeeded
    )
