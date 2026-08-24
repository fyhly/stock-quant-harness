from dataclasses import replace
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
    LiquidityBar,
    ShareObservation,
    SizeLiquidityFactors,
    size_liquidity_factors,
)


SECURITY = SecurityId("600000", Exchange.SHANGHAI)
CUTOFF = datetime(2024, 1, 4, tzinfo=timezone.utc)
DAYS = tuple(TradingDay(date(2024, 1, 1) + timedelta(days=i)) for i in range(4))
SESSION = TradingSession("day", time(9, 30), time(15))
CALENDAR = TradingCalendar(
    {d: (SESSION,) for d in DAYS},
    coverage_start=DAYS[0].value,
    coverage_end=DAYS[-1].value,
    timezone="Asia/Shanghai",
)
BARS = tuple(
    LiquidityBar(SECURITY, day, Decimal(10), 100, CUTOFF, "bars-v1")
    for day in DAYS[:-1]
)
SHARES = (ShareObservation(SECURITY, DAYS[0], CUTOFF, 1000, 500, "shares-v1"),)


def calculate(
    bars: Tuple[LiquidityBar, ...] = BARS,
    shares: Tuple[ShareObservation, ...] = SHARES,
) -> SizeLiquidityFactors:
    return size_liquidity_factors(
        bars,
        shares,
        security_id=SECURITY,
        decision_day=DAYS[-1],
        decision_cutoff=CUTOFF,
        calendar=CALENDAR,
        sessions=3,
        maximum_share_age_days=10,
    )


def test_exact_caps_turnover_coverage_and_versions() -> None:
    result = calculate()
    assert result.market_cap == Decimal(10000)
    assert result.float_cap == Decimal(5000)
    assert result.average_turnover == Decimal("0.2")
    assert result.share_versions == ("shares-v1",) * 3


def test_future_gapped_and_stale_inputs_fail_closed() -> None:
    with pytest.raises(FeatureContractError, match="future"):
        calculate(
            shares=(replace(SHARES[0], available_time=CUTOFF + timedelta(seconds=1)),)
        )
    with pytest.raises(FeatureContractError, match="future"):
        calculate(bars=BARS + (replace(BARS[-1], trading_day=DAYS[-1]),))
    with pytest.raises(FeatureContractError, match="gapped"):
        calculate(bars=BARS[:-1])
    with pytest.raises(FeatureContractError, match="stale"):
        size_liquidity_factors(
            BARS,
            SHARES,
            security_id=SECURITY,
            decision_day=DAYS[-1],
            decision_cutoff=CUTOFF,
            calendar=CALENDAR,
            sessions=3,
            maximum_share_age_days=1,
        )
