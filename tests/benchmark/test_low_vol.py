from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import pytest
from stock_quant.benchmark.low_vol import run_low_vol_benchmark
from stock_quant.domain import (
    Exchange,
    SecurityId,
    TradingCalendar,
    TradingDay,
    TradingSession,
)
from stock_quant.features import FeatureContractError, PriceObservation


def test_fixed_low_vol_direction_repeatability_and_missing_failure() -> None:
    ids = (
        SecurityId("600000", Exchange.SHANGHAI),
        SecurityId("600001", Exchange.SHANGHAI),
    )
    days = tuple(TradingDay(date(2024, 1, 1) + timedelta(days=i)) for i in range(22))
    cutoff = datetime(2024, 2, 1, tzinfo=timezone.utc)
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
            Decimal(10) if security == ids[0] else Decimal(10 + index % 2),
            cutoff,
            "raw",
        )
        for security in ids
        for index, day in enumerate(days[:-1])
    )
    first = run_low_vol_benchmark(
        rows, ids, decision_day=days[-1], decision_cutoff=cutoff, calendar=calendar
    )
    assert first == run_low_vol_benchmark(
        reversed(rows),
        reversed(ids),
        decision_day=days[-1],
        decision_cutoff=cutoff,
        calendar=calendar,
    )
    assert first.ranked[0].security_id == ids[0] and first.window == 20
    with pytest.raises(FeatureContractError, match="gapped"):
        run_low_vol_benchmark(
            rows[:-1],
            ids,
            decision_day=days[-1],
            decision_cutoff=cutoff,
            calendar=calendar,
        )
