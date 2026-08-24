"""Point-in-time size and session-exact liquidity factors."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Iterable, Tuple

from stock_quant.domain import SecurityId, TradingCalendar, TradingDay
from stock_quant.features.api import FeatureContractError


@dataclass(frozen=True)
class ShareObservation:
    security_id: SecurityId
    effective_day: TradingDay
    available_time: datetime
    total_shares: int
    float_shares: int
    version: str


@dataclass(frozen=True)
class LiquidityBar:
    security_id: SecurityId
    trading_day: TradingDay
    close: Decimal
    volume: int
    available_time: datetime
    source_identity: str


@dataclass(frozen=True)
class SizeLiquidityFactors:
    market_cap: Decimal
    float_cap: Decimal
    average_turnover: Decimal
    sessions: int
    share_versions: Tuple[str, ...]
    bar_identity: str


def size_liquidity_factors(
    bars: Iterable[LiquidityBar],
    shares: Iterable[ShareObservation],
    *,
    security_id: SecurityId,
    decision_day: TradingDay,
    decision_cutoff: datetime,
    calendar: TradingCalendar,
    sessions: int,
    maximum_share_age_days: int,
) -> SizeLiquidityFactors:
    raw_bars, raw_shares = tuple(bars), tuple(shares)
    if sessions <= 0 or maximum_share_age_days < 0:
        raise FeatureContractError("invalid window or share age")
    if any(row.available_time > decision_cutoff for row in raw_bars) or any(
        row.available_time > decision_cutoff for row in raw_shares
    ):
        raise FeatureContractError("future bar or shares supplied")
    if any(row.trading_day >= decision_day for row in raw_bars) or any(
        row.effective_day >= decision_day for row in raw_shares
    ):
        raise FeatureContractError("future bar or shares supplied")
    days = tuple(day for day in calendar.trading_days if day < decision_day)
    if len(days) < sessions:
        raise FeatureContractError("insufficient liquidity history")
    required = days[-sessions:]
    selected_bars = tuple(
        row
        for row in raw_bars
        if row.security_id == security_id and row.trading_day in required
    )
    by_day = {row.trading_day: row for row in selected_bars}
    if len(by_day) != len(selected_bars) or tuple(sorted(by_day)) != required:
        raise FeatureContractError("gapped or duplicate liquidity bars")
    eligible_shares = tuple(row for row in raw_shares if row.security_id == security_id)
    selected_shares = []
    turnovers = []
    for day in required:
        versions = tuple(row for row in eligible_shares if row.effective_day <= day)
        if not versions:
            raise FeatureContractError("missing historical shares")
        share = max(versions, key=lambda row: (row.effective_day, row.available_time))
        if (day.value - share.effective_day.value).days > maximum_share_age_days:
            raise FeatureContractError("stale historical shares")
        if share.total_shares <= 0 or not 0 < share.float_shares <= share.total_shares:
            raise FeatureContractError("invalid total or float shares")
        bar = by_day[day]
        if bar.close <= 0 or bar.volume < 0:
            raise FeatureContractError("invalid bar")
        selected_shares.append(share)
        turnovers.append(Decimal(bar.volume) / Decimal(share.float_shares))
    latest_bar = by_day[required[-1]]
    latest_share = selected_shares[-1]
    return SizeLiquidityFactors(
        latest_bar.close * Decimal(latest_share.total_shares),
        latest_bar.close * Decimal(latest_share.float_shares),
        sum(turnovers, Decimal(0)) / Decimal(sessions),
        sessions,
        tuple(item.version for item in selected_shares),
        latest_bar.source_identity,
    )
