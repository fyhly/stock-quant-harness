from datetime import date, time
from decimal import Decimal

from stock_quant.data import DailyBar, DailyBarSeries
from stock_quant.domain import (
    Exchange,
    ListingLifecycle,
    SecurityId,
    StatusInterval,
    STStatus,
    STStatusHistory,
    TradeStatus,
    TradeStatusHistory,
    TradingCalendar,
    TradingDay,
    TradingSession,
)
from stock_quant.universe import (
    ExclusionCode,
    HistoricalLiquidityFilter,
    HistoricalSTFilter,
    HistoricalTradeStatusFilter,
    IndexId,
    IndexMembership,
    IndexMembershipHistory,
    LiquidityPolicy,
    ListingHistoryFilter,
    SecurityMaster,
    SecurityMetadata,
    STEligibilityPolicy,
    UniverseEngine,
)


OLD_VALID = SecurityId("600000", Exchange.SHANGHAI)
CURRENT_ONLY = SecurityId("000001", Exchange.SHENZHEN)
DELISTED = SecurityId("600001", Exchange.SHANGHAI)
INDEX = IndexId("fixture-index")


def calendar() -> TradingCalendar:
    session = TradingSession("day", time(9, 30), time(15))
    days = [date(2020, 1, 2), date(2020, 1, 3), date(2020, 1, 6), date(2020, 1, 7)]
    return TradingCalendar(
        {TradingDay(day): (session,) for day in days},
        coverage_start=date(2020, 1, 1),
        coverage_end=date(2022, 1, 10),
        timezone="Asia/Shanghai",
    )


def bars(security_id: SecurityId, amount: str = "1000") -> DailyBarSeries:
    return DailyBarSeries(
        security_id,
        [
            DailyBar(
                security_id,
                TradingDay(day),
                Decimal("10"),
                Decimal("10"),
                Decimal("10"),
                Decimal("10"),
                100,
                Decimal(amount),
            )
            for day in (date(2020, 1, 3), date(2020, 1, 6))
        ],
    )


def test_historical_universe_blocks_survivor_and_current_state_leakage() -> None:
    securities = (OLD_VALID, CURRENT_ONLY, DELISTED)
    master = SecurityMaster(
        [SecurityMetadata(item, f"security-{index}") for index, item in enumerate(securities)]
    )
    listing = ListingHistoryFilter(
        {
            OLD_VALID: ListingLifecycle(OLD_VALID, date(2010, 1, 1), date(2021, 1, 1)),
            CURRENT_ONLY: ListingLifecycle(CURRENT_ONLY, date(2010, 1, 1)),
            DELISTED: ListingLifecycle(DELISTED, date(2000, 1, 1), date(2019, 1, 1)),
        }
    )
    st = HistoricalSTFilter(
        {
            OLD_VALID: STStatusHistory(
                [
                    StatusInterval(STStatus.NORMAL, date(2010, 1, 1), date(2021, 1, 1)),
                    StatusInterval(STStatus.ST, date(2021, 1, 1)),
                ]
            ),
            CURRENT_ONLY: STStatusHistory(
                [StatusInterval(STStatus.NORMAL, date(2010, 1, 1))]
            ),
            DELISTED: STStatusHistory(
                [StatusInterval(STStatus.NORMAL, date(2000, 1, 1))]
            ),
        },
        STEligibilityPolicy("exclude-st-v1"),
    )
    trade = HistoricalTradeStatusFilter(
        {
            item: TradeStatusHistory(
                [StatusInterval(TradeStatus.TRADING, date(2000, 1, 1))]
            )
            for item in securities
        }
    )
    index = IndexMembershipHistory(
        INDEX,
        [
            IndexMembership(INDEX, OLD_VALID, date(2019, 1, 1), date(2021, 1, 1)),
            IndexMembership(INDEX, CURRENT_ONLY, date(2021, 1, 1)),
            IndexMembership(INDEX, DELISTED, date(2000, 1, 1), date(2019, 1, 1)),
        ],
        coverage_start=date(2000, 1, 1),
        coverage_end=date(2022, 1, 1),
    )
    liquidity = HistoricalLiquidityFilter(
        calendar(), LiquidityPolicy("v1", 2, Decimal("100"), Decimal("1000"))
    )
    engine = UniverseEngine(
        rule_version="universe-v1",
        master=master,
        listing_filter=listing,
        st_filter=st,
        trade_filter=trade,
        index_history=index,
        liquidity_filter=liquidity,
        bars={item: bars(item) for item in securities},
    )

    result = engine.build(date(2020, 1, 7))

    assert result.included == (OLD_VALID,)
    reasons = {item.security_id: item.reasons for item in result.excluded}
    assert [reason.code for reason in reasons[CURRENT_ONLY]] == [
        ExclusionCode.NOT_INDEX_MEMBER
    ]
    assert ExclusionCode.DELISTED in [reason.code for reason in reasons[DELISTED]]
    # OLD_VALID is currently ST/delisted after 2021 but was correctly visible in 2020.


def test_missing_facts_fail_closed_in_fixed_reason_order() -> None:
    security = OLD_VALID
    engine = UniverseEngine(
        rule_version="universe-v1",
        master=SecurityMaster([SecurityMetadata(security, "missing-facts")]),
        listing_filter=ListingHistoryFilter({}),
        st_filter=HistoricalSTFilter({}, STEligibilityPolicy("v1")),
        trade_filter=HistoricalTradeStatusFilter({}),
        index_history=IndexMembershipHistory(
            INDEX,
            [],
            coverage_start=date(2021, 1, 1),
            coverage_end=date(2022, 1, 1),
        ),
        liquidity_filter=HistoricalLiquidityFilter(
            calendar(), LiquidityPolicy("v1", 2, Decimal(0), Decimal(0))
        ),
        bars={},
    )

    result = engine.build(date(2020, 1, 7))

    assert result.included == ()
    assert [reason.code for reason in result.excluded[0].reasons] == [
        ExclusionCode.MISSING_LISTING_HISTORY,
        ExclusionCode.MISSING_ST_HISTORY,
        ExclusionCode.MISSING_TRADE_STATUS_HISTORY,
        ExclusionCode.MISSING_INDEX_HISTORY,
        ExclusionCode.MISSING_LIQUIDITY_HISTORY,
    ]
