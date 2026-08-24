from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from stock_quant.domain import Exchange, SecurityId, TradingDay
from stock_quant.features import (
    FeatureContractError,
    FundamentalObservation,
    ValuationObservation,
    ValueFactors,
    value_factors,
)


SECURITY = SecurityId("600000", Exchange.SHANGHAI)
DAY = TradingDay(date(2024, 5, 1))
CUTOFF = datetime(2024, 5, 1, 6, tzinfo=timezone.utc)
VALUE = ValuationObservation(SECURITY, DAY, CUTOFF, Decimal(100), "market")
OLD = FundamentalObservation(
    SECURITY,
    date(2023, 12, 31),
    CUTOFF - timedelta(days=10),
    CUTOFF - timedelta(days=10),
    Decimal(10),
    Decimal(50),
    Decimal(80),
    "old",
)
REVISED = replace(
    OLD,
    revision_time=CUTOFF,
    net_income=Decimal(-5),
    equity=Decimal(0),
    revenue=None,
    source_identity="revision",
)


def calculate(facts: tuple[FundamentalObservation, ...] = (OLD,)) -> ValueFactors:
    return value_factors(
        (VALUE,),
        facts,
        security_id=SECURITY,
        decision_day=DAY,
        decision_cutoff=CUTOFF,
        maximum_valuation_age_days=1,
    )


def test_announcement_boundary_revision_and_undefined_semantics() -> None:
    original = calculate()
    revised = calculate((OLD, REVISED))
    assert original.pe == Decimal(10)
    assert revised.pe == Decimal(-20)
    assert revised.earnings_yield == Decimal("-0.05")
    assert revised.pb is None and revised.ps is None
    assert revised.lineage[-1] == "revision"


def test_future_stale_and_missing_data_fail_closed() -> None:
    with pytest.raises(FeatureContractError, match="future"):
        calculate((replace(OLD, announcement_time=CUTOFF + timedelta(seconds=1)),))
    with pytest.raises(FeatureContractError, match="stale"):
        value_factors(
            (replace(VALUE, trading_day=TradingDay(date(2024, 4, 1))),),
            (OLD,),
            security_id=SECURITY,
            decision_day=DAY,
            decision_cutoff=CUTOFF,
            maximum_valuation_age_days=1,
        )
    with pytest.raises(FeatureContractError, match="missing fundamental"):
        calculate(())
