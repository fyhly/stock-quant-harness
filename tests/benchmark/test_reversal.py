from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from stock_quant.benchmark import run_reversal_benchmark
from stock_quant.domain import (
    Exchange,
    SecurityId,
    TradingCalendar,
    TradingDay,
    TradingSession,
)
from stock_quant.features import PriceObservation


def test_fixed_reversal_sign_windows_and_determinism() -> None:
    ids = (
        SecurityId("600000", Exchange.SHANGHAI),
        SecurityId("600001", Exchange.SHANGHAI),
    )
    days = tuple(TradingDay(date(2024, 1, 1) + timedelta(days=i)) for i in range(12))
    cutoff = datetime(2024, 2, 1, tzinfo=timezone.utc)
    session = TradingSession("day", time(9, 30), time(15))
    calendar = TradingCalendar(
        {day: (session,) for day in days},
        coverage_start=days[0].value,
        coverage_end=days[-1].value,
        timezone="Asia/Shanghai",
    )
    rows = tuple(
        PriceObservation(security, day, Decimal(index + 1), cutoff, "raw")
        for security in ids
        for index, day in enumerate(days[:-1])
    )
    first = run_reversal_benchmark(
        rows,
        ids,
        decision_day=days[-1],
        decision_cutoff=cutoff,
        calendar=calendar,
        view_identity="raw",
    )
    assert first == run_reversal_benchmark(
        reversed(rows),
        reversed(ids),
        decision_day=days[-1],
        decision_cutoff=cutoff,
        calendar=calendar,
        view_identity="raw",
    )
    assert tuple(window for window, _ in first.scores) == (5, 10)
    assert first.sign == "negative_trailing_return"
