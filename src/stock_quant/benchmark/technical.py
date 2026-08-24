"""Fixed moving-average and prior-window breakout sanity benchmarks."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, Tuple
from stock_quant.domain import SecurityId, TradingCalendar, TradingDay
from stock_quant.features import FeatureContractError, PriceObservation


@dataclass(frozen=True)
class TechnicalSignal:
    security_id: SecurityId
    moving_average_20_above_60: bool
    prior_close_breakout_20: bool


@dataclass(frozen=True)
class TechnicalBenchmarkResult:
    decision_day: TradingDay
    next_session_eligible: TradingDay
    signals: Tuple[TechnicalSignal, ...]
    windows: Tuple[int, int, int] = (20, 60, 20)


def run_technical_benchmarks(
    observations: Iterable[PriceObservation],
    securities: Iterable[SecurityId],
    *,
    decision_day: TradingDay,
    calendar: TradingCalendar,
) -> TechnicalBenchmarkResult:
    rows = tuple(observations)
    if any(row.trading_day >= decision_day for row in rows):
        raise FeatureContractError("decision-bar or future observation rejected")
    required = tuple(day for day in calendar.trading_days if day < decision_day)[-61:]
    if len(required) != 61:
        raise FeatureContractError("insufficient technical history")
    output = []
    for security in tuple(securities):
        selected = tuple(
            row
            for row in rows
            if row.security_id == security and row.trading_day in required
        )
        by_day = {row.trading_day: row for row in selected}
        if len(by_day) != 61 or tuple(sorted(by_day)) != required:
            raise FeatureContractError("gapped or duplicate technical history")
        closes = tuple(by_day[day].close for day in required)
        ma20 = sum(closes[-20:], Decimal(0)) / Decimal(20)
        ma60 = sum(closes[-60:], Decimal(0)) / Decimal(60)
        breakout = closes[-1] > max(closes[-21:-1])
        output.append(TechnicalSignal(security, ma20 > ma60, breakout))
    return TechnicalBenchmarkResult(
        decision_day,
        calendar.next_trading_day(decision_day.value),
        tuple(sorted(output, key=lambda row: row.security_id)),
    )
