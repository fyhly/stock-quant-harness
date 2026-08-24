"""Deterministic composition of point-in-time Universe eligibility rules."""

from dataclasses import dataclass
from datetime import date
from typing import Mapping, Tuple

from stock_quant.data import DailyBarSeries
from stock_quant.domain import SecurityId
from stock_quant.universe.index import (
    IndexMembershipHistory,
    UnknownIndexHistoryError,
)
from stock_quant.universe.liquidity import HistoricalLiquidityFilter
from stock_quant.universe.master import SecurityMaster
from stock_quant.universe.rules import (
    Exclusion,
    ExclusionCode,
    HistoricalSTFilter,
    HistoricalTradeStatusFilter,
    ListingHistoryFilter,
)


@dataclass(frozen=True)
class SecurityExclusions:
    security_id: SecurityId
    reasons: Tuple[Exclusion, ...]

    def __post_init__(self) -> None:
        if not self.reasons:
            raise ValueError("excluded security must have at least one reason")


@dataclass(frozen=True)
class UniverseResult:
    as_of: date
    rule_version: str
    included: Tuple[SecurityId, ...]
    excluded: Tuple[SecurityExclusions, ...]


class UniverseEngine:
    """Evaluate every retained master identity in a fixed explainable order."""

    def __init__(
        self,
        *,
        rule_version: str,
        master: SecurityMaster,
        listing_filter: ListingHistoryFilter,
        st_filter: HistoricalSTFilter,
        trade_filter: HistoricalTradeStatusFilter,
        index_history: IndexMembershipHistory,
        liquidity_filter: HistoricalLiquidityFilter,
        bars: Mapping[SecurityId, DailyBarSeries],
    ) -> None:
        if not isinstance(rule_version, str) or not rule_version.strip():
            raise ValueError("rule_version must be non-empty")
        copied_bars = dict(bars)
        for security_id, series in copied_bars.items():
            if not isinstance(security_id, SecurityId):
                raise TypeError("bar keys must be SecurityId")
            if not isinstance(series, DailyBarSeries):
                raise TypeError("bar values must be DailyBarSeries")
            if series.security_id != security_id:
                raise ValueError("bar series identity mismatch")
        self.rule_version = rule_version
        self.master = master
        self.listing_filter = listing_filter
        self.st_filter = st_filter
        self.trade_filter = trade_filter
        self.index_history = index_history
        self.liquidity_filter = liquidity_filter
        self._bars = copied_bars

    def build(self, as_of: date) -> UniverseResult:
        if type(as_of) is not date:
            raise TypeError("as_of must be a date, not a datetime")
        included = []
        excluded = []
        for metadata in self.master.securities:
            security_id = metadata.security_id
            reasons = []
            for decision in (
                self.listing_filter.evaluate(security_id, as_of),
                self.st_filter.evaluate(security_id, as_of),
                self.trade_filter.evaluate(security_id, as_of),
            ):
                if decision.exclusion is not None:
                    reasons.append(decision.exclusion)
            try:
                is_member = self.index_history.is_member(security_id, as_of)
                if not is_member:
                    reasons.append(
                        Exclusion(
                            ExclusionCode.NOT_INDEX_MEMBER,
                            "index_membership",
                            "security is not a member of the requested index",
                            (("index_id", self.index_history.index_id.value),),
                        )
                    )
            except UnknownIndexHistoryError:
                reasons.append(
                    Exclusion(
                        ExclusionCode.MISSING_INDEX_HISTORY,
                        "index_membership",
                        "as-of date is outside complete index-history coverage",
                        (("index_id", self.index_history.index_id.value),),
                    )
                )
            liquidity = self.liquidity_filter.evaluate(
                security_id, self._bars.get(security_id), as_of
            )
            if liquidity.exclusion is not None:
                reasons.append(liquidity.exclusion)
            if reasons:
                excluded.append(SecurityExclusions(security_id, tuple(reasons)))
            else:
                included.append(security_id)
        return UniverseResult(
            as_of,
            self.rule_version,
            tuple(included),
            tuple(excluded),
        )
