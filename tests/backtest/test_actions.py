from datetime import date
from decimal import Decimal

import pytest

from stock_quant.actions import (
    BonusShareEvent,
    CashDividend,
    DuplicateActionApplicationError,
    FlatDividendTaxPolicy,
    FractionalSharePolicy,
    PositionState,
)
from stock_quant.backtest import (
    ActionIntegrationState,
    apply_pre_market_action,
    capture_record_entitlement,
    EventKind,
    EventPhase,
    TimelineEvent,
)
from stock_quant.domain import Exchange, SecurityId, TradingDay


SECURITY = SecurityId("600000", Exchange.SHANGHAI)
SOURCE = "a" * 64
RECORD = TradingDay(date(2024, 5, 8))
EX = TradingDay(date(2024, 5, 9))
PAY = TradingDay(date(2024, 5, 15))


def dividend() -> CashDividend:
    return CashDividend(
        SECURITY, date(2024, 1, 1), RECORD.value, EX.value, PAY.value,
        Decimal("0.3"), SOURCE, "v1"
    )


def record_event(event_id: str) -> TimelineEvent:
    return TimelineEvent(
        event_id, RECORD, EventPhase.RECORD_ENTITLEMENT, 0, EventKind.ENTITLEMENT
    )


def action_event(event_id: str, day: TradingDay, sequence: int = 0) -> TimelineEvent:
    return TimelineEvent(
        event_id, day, EventPhase.PRE_MARKET_ACTIONS, sequence,
        EventKind.CORPORATE_ACTION
    )


def test_record_close_quantity_then_ex_and_pay_stages() -> None:
    action = dividend()
    state = ActionIntegrationState(
        PositionState(SECURITY, 120, Decimal("1200"), Decimal("1000"))
    )
    state = capture_record_entitlement(
        state, action, record_event("record"),
        tax_policy=FlatDividendTaxPolicy("zero-v1", Decimal(0))
    )
    state = apply_pre_market_action(state, action, action_event("ex", EX))

    assert state.eligibility[0].quantity == 120
    assert state.position.dividend_receivable == Decimal("36.0")
    assert state.position.cash == Decimal("1000")
    state = apply_pre_market_action(state, action, action_event("pay", PAY))
    assert state.position.dividend_receivable == 0
    assert state.position.cash == Decimal("1036.0")


def test_share_credit_separation_and_nav_continuity() -> None:
    credit = TradingDay(date(2024, 5, 10))
    action = BonusShareEvent(
        SECURITY, date(2024, 1, 1), RECORD.value, EX.value, credit.value,
        Decimal("0.1"), Decimal("0.2"), SOURCE, "v1"
    )
    state = ActionIntegrationState(
        PositionState(SECURITY, 100, Decimal("1000"), Decimal("1000"))
    )
    state = capture_record_entitlement(state, action, record_event("bonus-record"))
    with pytest.raises(ValueError, match="share_credit_date"):
        apply_pre_market_action(
            state, action, action_event("early", EX),
            fractional_policy=FractionalSharePolicy.REJECT,
            pre_action_reference_price=Decimal("10")
        )
    applied = apply_pre_market_action(
        state, action, action_event("credit", credit),
        fractional_policy=FractionalSharePolicy.REJECT,
        pre_action_reference_price=Decimal("10")
    )
    assert applied.position.quantity == 130
    assert applied.position.nav(Decimal("10") / Decimal("1.3")) == state.position.nav(
        Decimal("10")
    )


def test_duplicate_replay_and_wrong_phase_are_rejected() -> None:
    action = dividend()
    state = capture_record_entitlement(
        ActionIntegrationState(
            PositionState(SECURITY, 100, Decimal("1000"), Decimal("1000"))
        ),
        action,
        record_event("record"),
        tax_policy=FlatDividendTaxPolicy("zero-v1", Decimal(0)),
    )
    state = apply_pre_market_action(state, action, action_event("ex", EX))
    with pytest.raises(DuplicateActionApplicationError):
        apply_pre_market_action(state, action, action_event("ex-replay", EX))
    with pytest.raises(ValueError, match="PRE_MARKET"):
        apply_pre_market_action(state, action, record_event("wrong"))
