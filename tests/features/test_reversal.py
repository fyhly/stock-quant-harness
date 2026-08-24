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
from stock_quant.features import (
    FeatureContractError,
    PriceObservation,
    short_term_reversal,
)


SECURITY = SecurityId("600000", Exchange.SHANGHAI)
CUTOFF = datetime(2024, 1, 20, tzinfo=timezone.utc)


def history() -> Tuple[TradingDay, TradingCalendar, Tuple[PriceObservation, ...]]:
    days = tuple(TradingDay(date(2024, 1, 1) + timedelta(days=i)) for i in range(12))
    session = TradingSession("day", time(9, 30), time(15))
    calendar = TradingCalendar(
        {d: (session,) for d in days},
        coverage_start=days[0].value,
        coverage_end=days[-1].value,
        timezone="Asia/Shanghai",
    )
    rows = tuple(
        PriceObservation(SECURITY, d, Decimal(i + 1), CUTOFF, "raw")
        for i, d in enumerate(days[:-1])
    )
    return days[-1], calendar, rows


def calculate(rows: Tuple[PriceObservation, ...], window: int) -> Decimal:
    day, calendar, _ = history()
    return short_term_reversal(
        rows,
        security_id=SECURITY,
        decision_day=day,
        decision_cutoff=CUTOFF,
        calendar=calendar,
        sessions=window,
        view_identity="raw",
    )


@pytest.mark.parametrize("window", (5, 10))
def test_reversal_is_negative_exact_trailing_return(window: int) -> None:
    _, _, rows = history()
    expected = -(rows[-1].close / rows[-(window + 1)].close - Decimal(1))
    assert calculate(rows, window) == expected


def test_gapped_and_future_history_fail() -> None:
    day, _, rows = history()
    with pytest.raises(FeatureContractError, match="gapped"):
        calculate(rows[-5:], 5)
    with pytest.raises(FeatureContractError, match="gapped"):
        calculate(rows[:-2] + rows[-1:], 5)
    future = rows + (PriceObservation(SECURITY, day, Decimal(12), CUTOFF, "raw"),)
    with pytest.raises(FeatureContractError, match="future"):
        calculate(future, 5)
