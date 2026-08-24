from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Tuple
from stock_quant.benchmark import MomentumBenchmarkConfig, run_momentum_benchmark
from stock_quant.domain import (
    Exchange,
    SecurityId,
    TradingCalendar,
    TradingDay,
    TradingSession,
)
from stock_quant.features import PriceObservation

IDS = (SecurityId("600000", Exchange.SHANGHAI), SecurityId("600001", Exchange.SHANGHAI))
CUTOFF = datetime(2024, 5, 1, tzinfo=timezone.utc)


def fixture() -> Tuple[TradingDay, TradingCalendar, Tuple[PriceObservation, ...]]:
    days = tuple(TradingDay(date(2024, 1, 1) + timedelta(days=i)) for i in range(122))
    session = TradingSession("day", time(9, 30), time(15))
    calendar = TradingCalendar(
        {day: (session,) for day in days},
        coverage_start=days[0].value,
        coverage_end=days[-1].value,
        timezone="Asia/Shanghai",
    )
    rows = tuple(
        PriceObservation(
            security,
            day,
            Decimal(index + 1) * (Decimal(2) if security == IDS[0] else Decimal(1)),
            CUTOFF,
            "raw",
        )
        for security in IDS
        for index, day in enumerate(days[:-1])
    )
    return days[-1], calendar, rows


def test_fixed_windows_identity_cutoff_and_deterministic_runs() -> None:
    day, calendar, rows = fixture()
    first = run_momentum_benchmark(
        rows,
        IDS,
        decision_day=day,
        decision_cutoff=CUTOFF,
        calendar=calendar,
        view_identity="raw",
    )
    assert first == run_momentum_benchmark(
        reversed(rows),
        reversed(IDS),
        decision_day=day,
        decision_cutoff=CUTOFF,
        calendar=calendar,
        view_identity="raw",
    )
    assert tuple(window for window, _ in first.scores) == (20, 60, 120)
    assert first.config_identity == MomentumBenchmarkConfig().identity
