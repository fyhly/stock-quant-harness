from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import pytest
from stock_quant.benchmark import run_technical_benchmarks
from stock_quant.domain import (
    Exchange,
    SecurityId,
    TradingCalendar,
    TradingDay,
    TradingSession,
)
from stock_quant.features import FeatureContractError, PriceObservation


def test_fixed_rolling_boundaries_next_session_and_determinism() -> None:
    security = SecurityId("600000", Exchange.SHANGHAI)
    days = tuple(TradingDay(date(2024, 1, 1) + timedelta(days=i)) for i in range(63))
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
            Decimal(index + 1),
            datetime(2024, 4, 1, tzinfo=timezone.utc),
            "raw",
        )
        for index, day in enumerate(days[:61])
    )
    result = run_technical_benchmarks(
        rows, (security,), decision_day=days[61], calendar=calendar
    )
    assert result == run_technical_benchmarks(
        reversed(rows), (security,), decision_day=days[61], calendar=calendar
    )
    assert (
        result.signals[0].moving_average_20_above_60
        and result.signals[0].prior_close_breakout_20
    )
    assert result.next_session_eligible == days[62]
    with pytest.raises(FeatureContractError, match="future"):
        run_technical_benchmarks(
            rows
            + (
                PriceObservation(
                    security,
                    days[61],
                    Decimal(100),
                    datetime(2024, 4, 1, tzinfo=timezone.utc),
                    "raw",
                ),
            ),
            (security,),
            decision_day=days[61],
            calendar=calendar,
        )
