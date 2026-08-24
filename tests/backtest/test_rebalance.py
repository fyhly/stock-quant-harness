from datetime import date, time
from decimal import Decimal

import pytest

from stock_quant.backtest import (
    AccountState,
    book_buy,
    create_rebalance_intent,
    OrderSide,
    plan_rebalance,
    RawMark,
    TargetWeight,
)
from stock_quant.domain import Exchange, SecurityId, TradingCalendar, TradingDay, TradingSession


FIRST = SecurityId("600000", Exchange.SHANGHAI)
SECOND = SecurityId("000001", Exchange.SHENZHEN)
D1 = TradingDay(date(2024, 1, 2))
D2 = TradingDay(date(2024, 1, 3))


def calendar() -> TradingCalendar:
    session = TradingSession("day", time(9, 30), time(15))
    return TradingCalendar(
        {D1: (session,), D2: (session,)},
        coverage_start=D1.value, coverage_end=D2.value, timezone="Asia/Shanghai"
    )


def test_weights_create_sell_first_buy_orders_and_residual_cash() -> None:
    account = book_buy(
        AccountState(Decimal("10000")), FIRST, D1,
        quantity=500, price=Decimal("10")
    )
    marks = {
        FIRST: RawMark(FIRST, D1, Decimal("10")),
        SECOND: RawMark(SECOND, D1, Decimal("20")),
    }
    intent = create_rebalance_intent(
        "rebalance-1", D1,
        [TargetWeight(SECOND, Decimal("0.4")), TargetWeight(FIRST, Decimal("0.2"))]
    )

    plan = plan_rebalance(intent, account=account, marks=marks, calendar=calendar())

    assert plan.pre_trade_equity == Decimal("10000")
    assert dict(plan.target_quantities) == {FIRST: 200, SECOND: 200}
    assert [order.side for order in plan.orders] == [OrderSide.SELL, OrderSide.BUY]
    assert plan.orders[0].fill_day == D2
    assert plan.residual_cash == Decimal("4000")


def test_input_order_is_deterministic_and_buy_rounds_to_board_lot() -> None:
    targets = [TargetWeight(FIRST, Decimal("0.333")), TargetWeight(SECOND, Decimal("0.1"))]
    marks = {
        FIRST: RawMark(FIRST, D1, Decimal("10")),
        SECOND: RawMark(SECOND, D1, Decimal("20")),
    }
    account = AccountState(Decimal("10000"))
    first = plan_rebalance(
        create_rebalance_intent("x", D1, targets),
        account=account, marks=marks, calendar=calendar()
    )
    reverse = plan_rebalance(
        create_rebalance_intent("x", D1, reversed(targets)),
        account=account, marks=marks, calendar=calendar()
    )

    assert first == reverse
    assert dict(first.target_quantities)[FIRST] == 300
    assert dict(first.target_quantities)[SECOND] == 0


def test_invalid_weights_and_missing_marks_fail() -> None:
    with pytest.raises(ValueError, match="sum above"):
        create_rebalance_intent(
            "bad", D1,
            [TargetWeight(FIRST, Decimal("0.6")), TargetWeight(SECOND, Decimal("0.5"))]
        )
    intent = create_rebalance_intent("missing", D1, [TargetWeight(FIRST, Decimal("0.5"))])
    with pytest.raises(ValueError, match="missing"):
        plan_rebalance(
            intent, account=AccountState(Decimal("10000")), marks={}, calendar=calendar()
        )
