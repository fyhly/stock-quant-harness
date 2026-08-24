from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

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
    trailing_volatility,
    VolatilityResult,
)


SECURITY = SecurityId("600000", Exchange.SHANGHAI)
CUTOFF = datetime(2024, 1, 10, tzinfo=timezone.utc)


def calculate(closes: tuple[Decimal, ...]) -> VolatilityResult:
    days = tuple(
        TradingDay(date(2024, 1, 1) + timedelta(days=i)) for i in range(len(closes) + 1)
    )
    session = TradingSession("day", time(9, 30), time(15))
    calendar = TradingCalendar(
        {d: (session,) for d in days},
        coverage_start=days[0].value,
        coverage_end=days[-1].value,
        timezone="Asia/Shanghai",
    )
    rows = tuple(
        PriceObservation(SECURITY, d, value, CUTOFF, "raw")
        for d, value in zip(days, closes)
    )
    return trailing_volatility(
        rows,
        security_id=SECURITY,
        decision_day=days[-1],
        decision_cutoff=CUTOFF,
        calendar=calendar,
        sessions=len(closes) - 1,
        annualization_sessions=1,
    )


def test_formula_constant_and_negative_returns() -> None:
    constant = calculate((Decimal(10), Decimal(10), Decimal(10)))
    mixed = calculate((Decimal(10), Decimal(12), Decimal(9)))
    assert constant.realized == constant.downside == 0
    assert mixed.realized > 0
    assert mixed.downside > 0


def test_minimum_cutoff_and_determinism() -> None:
    assert calculate((Decimal(10), Decimal(11), Decimal(12))) == calculate(
        (Decimal(10), Decimal(11), Decimal(12))
    )
    with pytest.raises(FeatureContractError, match="minimum"):
        calculate((Decimal(10), Decimal(11)))
