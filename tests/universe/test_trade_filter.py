from datetime import date

from stock_quant.domain import (
    Exchange,
    SecurityId,
    StatusInterval,
    TradeStatus,
    TradeStatusHistory,
)
from stock_quant.universe import ExclusionCode, HistoricalTradeStatusFilter


SECURITY = SecurityId("600000", Exchange.SHANGHAI)


def test_suspension_boundaries_are_explainable_historical_feasibility() -> None:
    rule = HistoricalTradeStatusFilter(
        {
            SECURITY: TradeStatusHistory(
                [
                    StatusInterval(
                        TradeStatus.TRADING, date(2024, 1, 1), date(2024, 1, 8)
                    ),
                    StatusInterval(
                        TradeStatus.SUSPENDED,
                        date(2024, 1, 8),
                        date(2024, 1, 10),
                    ),
                    StatusInterval(TradeStatus.TRADING, date(2024, 1, 10)),
                ]
            )
        }
    )

    assert rule.evaluate(SECURITY, date(2024, 1, 7)).eligible
    suspended = rule.evaluate(SECURITY, date(2024, 1, 8))
    assert suspended.exclusion is not None
    assert suspended.exclusion.code is ExclusionCode.SUSPENDED
    assert suspended.exclusion.evidence == (("status", "SUSPENDED"),)
    assert rule.evaluate(SECURITY, date(2024, 1, 10)).eligible


def test_missing_and_gapped_trade_history_fail_closed() -> None:
    missing = HistoricalTradeStatusFilter({})
    gapped = HistoricalTradeStatusFilter(
        {
            SECURITY: TradeStatusHistory(
                [
                    StatusInterval(
                        TradeStatus.TRADING, date(2024, 1, 1), date(2024, 1, 2)
                    ),
                    StatusInterval(TradeStatus.TRADING, date(2024, 1, 3)),
                ]
            )
        }
    )

    for rule in (missing, gapped):
        result = rule.evaluate(SECURITY, date(2024, 1, 2))
        assert result.exclusion is not None
        assert result.exclusion.code is ExclusionCode.MISSING_TRADE_STATUS_HISTORY
