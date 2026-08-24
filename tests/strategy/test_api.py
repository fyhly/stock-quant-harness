from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from stock_quant.domain import Exchange, SecurityId, TradingDay
from stock_quant.strategy import (
    create_score_intent,
    FeatureScore,
    StrategyContractError,
)


IDS = (SecurityId("600000", Exchange.SHANGHAI), SecurityId("600001", Exchange.SHANGHAI))
CUTOFF = datetime(2024, 1, 2, 7, tzinfo=timezone.utc)
HASH = "a" * 64


def score(security: SecurityId, available: datetime = CUTOFF) -> FeatureScore:
    return FeatureScore(security, Decimal(1), available, HASH)


def test_alignment_and_input_order_are_deterministic_without_execution() -> None:
    kwargs = dict(
        universe_identity=HASH, config_identity="b" * 64, data_identity="c" * 64
    )
    first = create_score_intent(
        TradingDay(date(2024, 1, 2)), CUTOFF, (score(IDS[1]), score(IDS[0])), **kwargs
    )
    second = create_score_intent(
        TradingDay(date(2024, 1, 2)), CUTOFF, (score(IDS[0]), score(IDS[1])), **kwargs
    )
    assert first == second
    assert all(
        "execution" not in value
        for value in vars(__import__("stock_quant.strategy", fromlist=["*"])).keys()
    )


def test_future_duplicate_missing_and_identity_fail_closed() -> None:
    kwargs = dict(universe_identity=HASH, config_identity=HASH, data_identity=HASH)
    with pytest.raises(StrategyContractError, match="unavailable"):
        create_score_intent(
            TradingDay(date(2024, 1, 2)),
            CUTOFF,
            (score(IDS[0], CUTOFF + timedelta(seconds=1)),),
            **kwargs,
        )
    with pytest.raises(StrategyContractError, match="unique"):
        create_score_intent(
            TradingDay(date(2024, 1, 2)),
            CUTOFF,
            (score(IDS[0]), score(IDS[0])),
            **kwargs,
        )
    with pytest.raises(StrategyContractError, match="lineage"):
        create_score_intent(
            TradingDay(date(2024, 1, 2)),
            CUTOFF,
            (score(IDS[0]),),
            universe_identity="bad",
            config_identity=HASH,
            data_identity=HASH,
        )
