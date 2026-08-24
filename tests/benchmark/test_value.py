from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import pytest
from stock_quant.benchmark import run_value_benchmark
from stock_quant.domain import Exchange, SecurityId, TradingDay
from stock_quant.features import (
    FeatureContractError,
    FundamentalObservation,
    ValuationObservation,
)


def test_value_pit_revision_invalid_denominator_and_determinism() -> None:
    ids = (
        SecurityId("600000", Exchange.SHANGHAI),
        SecurityId("600001", Exchange.SHANGHAI),
    )
    day, cutoff = (
        TradingDay(date(2024, 5, 1)),
        datetime(2024, 5, 1, tzinfo=timezone.utc),
    )
    values = tuple(
        ValuationObservation(sid, day, cutoff, Decimal(100), f"v{index}")
        for index, sid in enumerate(ids)
    )
    facts = tuple(
        FundamentalObservation(
            sid,
            date(2023, 12, 31),
            cutoff - timedelta(days=1),
            cutoff - timedelta(days=1),
            Decimal(10 - index),
            Decimal(50),
            Decimal(80),
            f"f{index}",
        )
        for index, sid in enumerate(ids)
    )
    first = run_value_benchmark(
        values, facts, ids, decision_day=day, decision_cutoff=cutoff
    )
    assert first == run_value_benchmark(
        reversed(values),
        reversed(facts),
        reversed(ids),
        decision_day=day,
        decision_cutoff=cutoff,
    )
    assert first.ranked[0][0] == ids[0]
    zero = replace(facts[0], net_income=Decimal(0))
    assert run_value_benchmark(
        values, (zero, facts[1]), ids, decision_day=day, decision_cutoff=cutoff
    ).ranked[-1] == (ids[0], Decimal(0))
    with pytest.raises(FeatureContractError, match="future"):
        run_value_benchmark(
            values,
            (replace(facts[0], revision_time=cutoff + timedelta(seconds=1)), facts[1]),
            ids,
            decision_day=day,
            decision_cutoff=cutoff,
        )
    with pytest.raises(FeatureContractError, match="market cap"):
        run_value_benchmark(
            (replace(values[0], market_cap=Decimal(0)), values[1]),
            facts,
            ids,
            decision_day=day,
            decision_cutoff=cutoff,
        )
