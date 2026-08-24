"""V1 cross-module semantic invariants, independent of milestone tests."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from stock_quant.actions import CashDividend, ForwardAdjustedBar
from stock_quant.actions.views import ResearchPriceExecutionError
from stock_quant.daily.quality import (
    DailyQualityEvidence,
    DailyQualityFailure,
    invoke_after_quality,
)
from stock_quant.domain import SecurityId, TradingDay
from stock_quant.e2e import run_real_backtest
from stock_quant.oos.train import BoundedAccessError, TrainContext
from stock_quant.oos.windows import OOSWindowSet, TimeWindow
from stock_quant.universe import (
    IndustryMembership,
    IndustryMembershipHistory,
    IndustryTaxonomy,
    SecurityMaster,
    SecurityMetadata,
)


SECURITY = SecurityId.parse("600000.XSHG")
REAL_ROOT = Path(__file__).parents[1] / "tests/fixtures/real/v1"
EXPECTED_REAL_FINGERPRINT = (
    "b6b4be7b4917c65f6ba03cca6a4a1f231266034dbc39803a80dfa3fc2fca1e96"
)


def test_pit_survivorship_and_action_execution_boundaries() -> None:
    master = SecurityMaster((SecurityMetadata(SECURITY, "retained delisted identity"),))
    assert master.get(SECURITY).security_id == SECURITY
    taxonomy = IndustryTaxonomy("AUDIT", "v1")
    history = IndustryMembershipHistory(
        taxonomy,
        (
            IndustryMembership(
                taxonomy, SECURITY, "OLD", date(2010, 1, 1), date(2020, 1, 1)
            ),
            IndustryMembership(taxonomy, SECURITY, "NEW", date(2020, 1, 1)),
        ),
    )
    assert (
        history.classification_as_of(SECURITY, date(2019, 1, 1)).industry_code == "OLD"
    )
    action = CashDividend(
        SECURITY,
        date(2024, 1, 1),
        date(2024, 1, 2),
        date(2024, 1, 3),
        date(2024, 1, 8),
        Decimal("0.1"),
        "a" * 64,
        "v1",
    )
    assert action.ex_date < action.pay_date
    adjusted = ForwardAdjustedBar(
        SECURITY,
        TradingDay(date(2024, 1, 2)),
        Decimal(1),
        Decimal(1),
        Decimal(1),
        Decimal(1),
        Decimal(1),
        1,
        Decimal(1),
        "factor",
        (),
    )
    with pytest.raises(ResearchPriceExecutionError):
        adjusted.as_execution_price()


def test_oos_context_and_daily_fatal_gate_are_capability_bounded() -> None:
    windows = OOSWindowSet.create(
        TimeWindow(date(2024, 1, 1), date(2024, 1, 3)),
        TimeWindow(date(2024, 1, 3), date(2024, 1, 4)),
        TimeWindow(date(2024, 1, 4), date(2024, 1, 5)),
    )
    context = TrainContext(
        windows, {date(2024, 1, 1): "train", date(2024, 1, 4): "oos"}
    )
    with pytest.raises(BoundedAccessError):
        context.get(date(2024, 1, 4))
    calls = []
    with pytest.raises(DailyQualityFailure):
        invoke_after_quality(
            DailyQualityEvidence(False, ("HASH",), (), ()),
            lambda: calls.append("downstream"),
        )
    assert calls == []


def test_real_e2e_replay_fingerprint_is_frozen_and_next_session() -> None:
    decision_day = TradingDay(date(2024, 11, 29))
    first = run_real_backtest(REAL_ROOT, decision_day)
    second = run_real_backtest(REAL_ROOT, decision_day)
    assert first == second and first.fingerprint == EXPECTED_REAL_FINGERPRINT
    assert all(fill.trading_day > decision_day for fill in first.fills)
