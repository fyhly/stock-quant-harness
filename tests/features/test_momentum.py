from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Tuple

import pytest

from stock_quant.domain import (
    Exchange,
    SecurityId,
    TradingCalendar,
    TradingDay,
    TradingSession,
)
from stock_quant.features import FeatureContractError, PriceObservation, trailing_return


SECURITY = SecurityId("600000", Exchange.SHANGHAI)
CUTOFF = datetime(2024, 5, 1, 6, tzinfo=timezone.utc)


def facts(
    count: int = 121, scale: Decimal = Decimal(1)
) -> Tuple[TradingDay, TradingCalendar, Tuple[PriceObservation, ...]]:
    days = tuple(
        TradingDay(date(2024, 1, 1) + timedelta(days=i)) for i in range(count + 1)
    )
    session = TradingSession("day", time(9, 30), time(15))
    calendar = TradingCalendar(
        {day: (session,) for day in days},
        coverage_start=days[0].value,
        coverage_end=days[-1].value,
        timezone="Asia/Shanghai",
    )
    rows = tuple(
        PriceObservation(SECURITY, day, scale * Decimal(i + 1), CUTOFF, "raw-v1")
        for i, day in enumerate(days[:-1])
    )
    return days[-1], calendar, rows


def calculate(
    rows: Tuple[PriceObservation, ...],
    decision: TradingDay,
    calendar: TradingCalendar,
    window: int,
) -> Decimal:
    return trailing_return(
        rows,
        security_id=SECURITY,
        decision_day=decision,
        decision_cutoff=CUTOFF,
        calendar=calendar,
        sessions=window,
        view_identity="raw-v1",
    )


@pytest.mark.parametrize("window", (20, 60, 120))
def test_exact_windows_and_scale_invariance(window: int) -> None:
    decision, calendar, rows = facts()
    scaled = tuple(
        PriceObservation(
            r.security_id, r.trading_day, r.close * 7, r.available_time, r.view_identity
        )
        for r in rows
    )
    assert calculate(rows, decision, calendar, window) == calculate(
        scaled, decision, calendar, window
    )


def test_gap_cutoff_and_future_rows_fail_closed() -> None:
    decision, calendar, rows = facts()
    with pytest.raises(FeatureContractError, match="gapped"):
        calculate(rows[:-2] + rows[-1:], decision, calendar, 20)
    unavailable = rows[:-1] + (
        PriceObservation(
            SECURITY,
            rows[-1].trading_day,
            rows[-1].close,
            CUTOFF + timedelta(seconds=1),
            "raw-v1",
        ),
    )
    with pytest.raises(FeatureContractError, match="unavailable"):
        calculate(unavailable, decision, calendar, 20)
    future = rows + (
        PriceObservation(SECURITY, decision, Decimal(1), CUTOFF, "raw-v1"),
    )
    with pytest.raises(FeatureContractError, match="future"):
        calculate(future, decision, calendar, 20)
