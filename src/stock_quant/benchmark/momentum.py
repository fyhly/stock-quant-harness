"""Predefined momentum calibration benchmarks; never parameter search."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from typing import Iterable, Tuple

from stock_quant.domain import SecurityId, TradingCalendar, TradingDay
from stock_quant.features import PriceObservation, trailing_return


@dataclass(frozen=True)
class MomentumBenchmarkConfig:
    windows: Tuple[int, ...] = (20, 60, 120)
    ascending: bool = False
    version: str = "momentum-benchmark-v1"

    @property
    def identity(self) -> str:
        content = json.dumps(
            {
                "ascending": self.ascending,
                "version": self.version,
                "windows": self.windows,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(content.encode()).hexdigest()


@dataclass(frozen=True)
class MomentumBenchmarkResult:
    config_identity: str
    decision_day: TradingDay
    scores: Tuple[Tuple[int, Tuple[Tuple[SecurityId, Decimal], ...]], ...]


def run_momentum_benchmark(
    observations: Iterable[PriceObservation],
    securities: Iterable[SecurityId],
    *,
    decision_day: TradingDay,
    decision_cutoff: datetime,
    calendar: TradingCalendar,
    view_identity: str,
) -> MomentumBenchmarkResult:
    config = MomentumBenchmarkConfig()
    rows = tuple(observations)
    security_ids = tuple(securities)
    output = []
    for window in config.windows:
        scores = tuple(
            sorted(
                (
                    (
                        security,
                        trailing_return(
                            rows,
                            security_id=security,
                            decision_day=decision_day,
                            decision_cutoff=decision_cutoff,
                            calendar=calendar,
                            sessions=window,
                            view_identity=view_identity,
                        ),
                    )
                    for security in security_ids
                ),
                key=lambda item: (-item[1], item[0]),
            )
        )
        output.append((window, scores))
    return MomentumBenchmarkResult(config.identity, decision_day, tuple(output))
