from datetime import date
from decimal import Decimal

from stock_quant.actions import RawExecutionBar
from stock_quant.backtest import (
    evaluate_price_limit,
    fill_price_within_limits,
    OrderSide,
    PriceLimitRule,
    PriceLimitSchedule,
    RejectionCode,
)
from stock_quant.domain import Exchange, MarketSegment, SecurityId, STStatus, TradingDay


MAIN = SecurityId("600000", Exchange.SHANGHAI)
CHINEXT = SecurityId("300001", Exchange.SHENZHEN)


def schedule() -> PriceLimitSchedule:
    return PriceLimitSchedule(
        "limits-v1",
        [
            PriceLimitRule(MarketSegment.MAIN_BOARD, date(2000, 1, 1), None, Decimal("0.10")),
            PriceLimitRule(
                MarketSegment.MAIN_BOARD, date(2000, 1, 1), None,
                Decimal("0.05"), STStatus.ST
            ),
            PriceLimitRule(
                MarketSegment.CHINEXT, date(2010, 1, 1), date(2020, 8, 24),
                Decimal("0.10")
            ),
            PriceLimitRule(
                MarketSegment.CHINEXT, date(2020, 8, 24), None, Decimal("0.20")
            ),
        ],
    )


def raw_bar(
    security: SecurityId, day: date, open_: str, high: str, low: str, close: str
) -> RawExecutionBar:
    return RawExecutionBar(
        security, TradingDay(day), Decimal(open_), Decimal(high), Decimal(low),
        Decimal(close), 1000, Decimal("10000"), "daily-bar-v1"
    )


def test_one_price_upper_and_lower_are_directional() -> None:
    upper = raw_bar(MAIN, date(2024, 1, 2), "11", "11", "11", "11")
    lower = raw_bar(MAIN, date(2024, 1, 2), "9", "9", "9", "9")

    assert evaluate_price_limit(
        schedule(), upper, prior_close=Decimal("10"),
        st_status=STStatus.NORMAL, side=OrderSide.BUY
    )[0].rejection is RejectionCode.PRICE_LIMIT
    assert evaluate_price_limit(
        schedule(), upper, prior_close=Decimal("10"),
        st_status=STStatus.NORMAL, side=OrderSide.SELL
    )[0].allowed
    assert evaluate_price_limit(
        schedule(), lower, prior_close=Decimal("10"),
        st_status=STStatus.NORMAL, side=OrderSide.SELL
    )[0].rejection is RejectionCode.PRICE_LIMIT
    assert evaluate_price_limit(
        schedule(), lower, prior_close=Decimal("10"),
        st_status=STStatus.NORMAL, side=OrderSide.BUY
    )[0].allowed


def test_non_one_price_limit_touch_is_allowed_but_fill_stays_in_ranges() -> None:
    bar = raw_bar(MAIN, date(2024, 1, 2), "10.5", "11", "10", "11")
    decision, band = evaluate_price_limit(
        schedule(), bar, prior_close=Decimal("10"),
        st_status=STStatus.NORMAL, side=OrderSide.BUY
    )

    assert decision.allowed and band is not None
    assert fill_price_within_limits(Decimal("10.8"), bar, band)
    assert not fill_price_within_limits(Decimal("11.01"), bar, band)


def test_board_date_st_and_rounding_boundaries() -> None:
    old = schedule().band(
        MarketSegment.CHINEXT, STStatus.NORMAL, date(2020, 8, 23), Decimal("10.01")
    )
    new = schedule().band(
        MarketSegment.CHINEXT, STStatus.NORMAL, date(2020, 8, 24), Decimal("10.01")
    )
    st = schedule().band(
        MarketSegment.MAIN_BOARD, STStatus.ST, date(2024, 1, 2), Decimal("10.01")
    )

    assert old.upper == Decimal("11.01")
    assert new.upper == Decimal("12.01")
    assert st.upper == Decimal("10.51")


def test_missing_facts_fail_closed() -> None:
    bar = raw_bar(MAIN, date(2024, 1, 2), "10", "10", "10", "10")
    decision, band = evaluate_price_limit(
        schedule(), bar, prior_close=None, st_status=STStatus.NORMAL, side=OrderSide.BUY
    )

    assert decision.rejection is RejectionCode.MISSING_PRICE_LIMIT_FACTS
    assert band is None
