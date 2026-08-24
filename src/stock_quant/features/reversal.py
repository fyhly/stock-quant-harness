"""Short-horizon reversal with the shared point-in-time session contract."""

from datetime import datetime
from decimal import Decimal
from typing import Iterable

from stock_quant.domain import SecurityId, TradingCalendar, TradingDay
from stock_quant.features.api import FeatureContractError
from stock_quant.features.momentum import PriceObservation, session_return


def short_term_reversal(
    observations: Iterable[PriceObservation],
    *,
    security_id: SecurityId,
    decision_day: TradingDay,
    decision_cutoff: datetime,
    calendar: TradingCalendar,
    sessions: int,
    view_identity: str,
) -> Decimal:
    if sessions not in (5, 10):
        raise FeatureContractError("reversal sessions must be 5 or 10")
    return -session_return(
        observations,
        security_id=security_id,
        decision_day=decision_day,
        decision_cutoff=decision_cutoff,
        calendar=calendar,
        sessions=sessions,
        view_identity=view_identity,
    )
