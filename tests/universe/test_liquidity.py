from datetime import date, time
from decimal import Decimal

from stock_quant.data import DailyBar, DailyBarSeries
from stock_quant.domain import (
    Exchange,
    SecurityId,
    TradingCalendar,
    TradingDay,
    TradingSession,
)
from stock_quant.universe import (
    ExclusionCode,
    HistoricalLiquidityFilter,
    LiquidityPolicy,
)


SECURITY = SecurityId("600000", Exchange.SHANGHAI)


def calendar() -> TradingCalendar:
    session = TradingSession("day", time(9, 30), time(15))
    return TradingCalendar(
        {
            TradingDay(date(2024, 1, day)): (session,)
            for day in (2, 3, 4, 5, 8, 9)
        },
        coverage_start=date(2024, 1, 1),
        coverage_end=date(2024, 1, 10),
        timezone="Asia/Shanghai",
    )


def series(*days: int, volume: int = 100, amount: str = "1000") -> DailyBarSeries:
    return DailyBarSeries(
        SECURITY,
        [
            DailyBar(
                SECURITY,
                TradingDay(date(2024, 1, day)),
                Decimal("10"),
                Decimal("10"),
                Decimal("10"),
                Decimal("10"),
                volume,
                Decimal(amount),
            )
            for day in days
        ],
    )


def rule() -> HistoricalLiquidityFilter:
    return HistoricalLiquidityFilter(
        calendar(),
        LiquidityPolicy("liquidity-v1", 3, Decimal("100"), Decimal("1000")),
    )


def test_threshold_equality_passes_with_deterministic_window() -> None:
    first = rule().evaluate(SECURITY, series(4, 5, 8), date(2024, 1, 9))
    second = rule().evaluate(SECURITY, series(4, 5, 8), date(2024, 1, 9))

    assert first.eligible
    assert first == second


def test_below_threshold_has_explicit_window_evidence() -> None:
    decision = rule().evaluate(
        SECURITY, series(4, 5, 8, volume=99), date(2024, 1, 9)
    )

    assert decision.exclusion is not None
    assert decision.exclusion.code is ExclusionCode.INSUFFICIENT_LIQUIDITY
    assert ("window_start", "2024-01-04") in decision.exclusion.evidence
    assert ("window_end", "2024-01-08") in decision.exclusion.evidence


def test_insufficient_and_gapped_history_fail_closed() -> None:
    insufficient = rule().evaluate(SECURITY, None, date(2024, 1, 9))
    gapped = rule().evaluate(SECURITY, series(4, 8), date(2024, 1, 9))

    for decision in (insufficient, gapped):
        assert decision.exclusion is not None
        assert decision.exclusion.code is ExclusionCode.MISSING_LIQUIDITY_HISTORY


def test_future_or_decision_day_row_is_rejected_not_ignored() -> None:
    decision = rule().evaluate(
        SECURITY, series(4, 5, 8, 9), date(2024, 1, 9)
    )

    assert decision.exclusion is not None
    assert decision.exclusion.code is ExclusionCode.FUTURE_LIQUIDITY_DATA
    assert decision.exclusion.evidence == (("first_rejected_date", "2024-01-09"),)


def test_no_weekday_assumption_in_window() -> None:
    # Jan 6/7 are weekends and are absent solely because the injected calendar says so.
    assert rule().evaluate(SECURITY, series(4, 5, 8), date(2024, 1, 9)).eligible
