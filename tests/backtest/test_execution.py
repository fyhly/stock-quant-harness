from datetime import date, time
from decimal import Decimal
from typing import Any

from stock_quant.actions import RawExecutionBar, RawExecutionPriceView
from stock_quant.backtest import (
    AccountState,
    book_buy,
    execute_next_open,
    OrderIntent,
    OrderSide,
    PriceLimitRule,
    PriceLimitSchedule,
    RejectionCode,
    SlippageModel,
    SuspensionConstraint,
    TradingCostRule,
    TradingCostSchedule,
)
from stock_quant.domain import (
    Exchange,
    MarketSegment,
    SecurityId,
    StatusInterval,
    STStatus,
    TradeStatus,
    TradeStatusHistory,
    TradingCalendar,
    TradingDay,
    TradingSession,
)


SECURITY = SecurityId("600000", Exchange.SHANGHAI)
D1 = TradingDay(date(2024, 1, 2))
D2 = TradingDay(date(2024, 1, 3))


def dependencies(volume: int = 1000, cash: str = "10000") -> Any:
    session = TradingSession("day", time(9, 30), time(15))
    calendar = TradingCalendar(
        {D1: (session,), D2: (session,)},
        coverage_start=D1.value, coverage_end=D2.value, timezone="Asia/Shanghai"
    )
    bar = RawExecutionBar(
        SECURITY, D2, Decimal("10"), Decimal("10.2"), Decimal("9.8"),
        Decimal("10"), volume, Decimal("10000"), "daily-bar-v1"
    )
    return {
        "view": RawExecutionPriceView(SECURITY, (bar,)),
        "account": AccountState(Decimal(cash)),
        "calendar": calendar,
        "suspension": SuspensionConstraint(
            {SECURITY: TradeStatusHistory([StatusInterval(TradeStatus.TRADING, D1.value)])}
        ),
        "price_limits": PriceLimitSchedule(
            "v1", [PriceLimitRule(MarketSegment.MAIN_BOARD, date(2000, 1, 1), None, Decimal("0.1"))]
        ),
        "prior_close": Decimal("10"),
        "st_status": STStatus.NORMAL,
        "costs": TradingCostSchedule(
            "v1", [TradingCostRule(date(2000, 1, 1), None, Decimal("0.0003"),
            Decimal("5"), Decimal(0), Decimal(0), Decimal("0.0005"))]
        ),
        "slippage": SlippageModel("slip-v1", Decimal("100")),
        "participation_cap": Decimal("0.25"),
    }


def order(side: OrderSide, quantity: int) -> OrderIntent:
    return OrderIntent("order-1", SECURITY, side, quantity, D1, D2)


def test_buy_partial_fill_volume_lot_slippage_cost_and_cash() -> None:
    outcome = execute_next_open(order(OrderSide.BUY, 500), **dependencies())

    assert outcome.fill is not None
    assert outcome.fill.quantity == 200  # floor(1000*25%) then 100-share lots
    assert outcome.fill.price == Decimal("10.1")
    assert outcome.account.cash == Decimal("10000") - Decimal("2020") - Decimal("5")


def test_zero_volume_and_exact_cash_fee_recalculation() -> None:
    zero = execute_next_open(order(OrderSide.BUY, 100), **dependencies(volume=0))
    tight = execute_next_open(order(OrderSide.BUY, 200), **dependencies(cash="1500"))

    assert zero.rejection is RejectionCode.ZERO_VOLUME
    assert tight.fill is not None and tight.fill.quantity == 100
    assert tight.account.cash == Decimal("485")


def test_sell_odd_lot_only_as_full_exit_and_t1_quantity() -> None:
    deps = dependencies()
    account = book_buy(
        AccountState(Decimal("10000")), SECURITY, D1,
        quantity=150, price=Decimal("10")
    )
    deps["account"] = account
    full = execute_next_open(order(OrderSide.SELL, 150), **deps)
    deps["account"] = account
    partial = execute_next_open(order(OrderSide.SELL, 50), **deps)

    assert full.fill is not None and full.fill.quantity == 150
    assert partial.rejection is RejectionCode.INSUFFICIENT_QUANTITY


def test_result_is_deterministic_and_next_day_is_required() -> None:
    first = execute_next_open(order(OrderSide.BUY, 100), **dependencies())
    second = execute_next_open(order(OrderSide.BUY, 100), **dependencies())
    invalid = OrderIntent("bad", SECURITY, OrderSide.BUY, 100, D2, D2)

    assert first == second
    assert execute_next_open(invalid, **dependencies()).rejection is (
        RejectionCode.INVALID_FILL_TIMING
    )
