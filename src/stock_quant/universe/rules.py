"""Explainable point-in-time eligibility rule results."""

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Mapping, Optional, Tuple

from stock_quant.domain import (
    ListingLifecycle,
    ListingStatus,
    SecurityId,
    STStatus,
    STStatusHistory,
    TradeStatus,
    TradeStatusHistory,
    UnknownStatusError,
)


class ExclusionCode(str, Enum):
    PRE_LISTING = "PRE_LISTING"
    DELISTED = "DELISTED"
    MISSING_LISTING_HISTORY = "MISSING_LISTING_HISTORY"
    ST_STATUS = "ST_STATUS"
    MISSING_ST_HISTORY = "MISSING_ST_HISTORY"
    SUSPENDED = "SUSPENDED"
    MISSING_TRADE_STATUS_HISTORY = "MISSING_TRADE_STATUS_HISTORY"
    NOT_INDEX_MEMBER = "NOT_INDEX_MEMBER"
    MISSING_INDEX_HISTORY = "MISSING_INDEX_HISTORY"
    INSUFFICIENT_LIQUIDITY = "INSUFFICIENT_LIQUIDITY"
    MISSING_LIQUIDITY_HISTORY = "MISSING_LIQUIDITY_HISTORY"
    FUTURE_LIQUIDITY_DATA = "FUTURE_LIQUIDITY_DATA"


@dataclass(frozen=True)
class Exclusion:
    code: ExclusionCode
    rule: str
    message: str
    evidence: Tuple[Tuple[str, str], ...] = ()


@dataclass(frozen=True)
class RuleDecision:
    eligible: bool
    exclusion: Optional[Exclusion] = None

    def __post_init__(self) -> None:
        if self.eligible == (self.exclusion is not None):
            raise ValueError("eligible decisions have no exclusion; failures require one")

    @classmethod
    def include(cls) -> "RuleDecision":
        return cls(True)

    @classmethod
    def exclude(cls, exclusion: Exclusion) -> "RuleDecision":
        return cls(False, exclusion)


class ListingHistoryFilter:
    """Eligibility from injected immutable listing lifecycles."""

    def __init__(self, histories: Mapping[SecurityId, ListingLifecycle]) -> None:
        copied = dict(histories)
        for security_id, lifecycle in copied.items():
            if not isinstance(security_id, SecurityId):
                raise TypeError("listing history keys must be SecurityId")
            if not isinstance(lifecycle, ListingLifecycle):
                raise TypeError("listing histories must be ListingLifecycle")
            if lifecycle.security_id != security_id:
                raise ValueError("listing lifecycle identity does not match its key")
        self._histories = copied

    def evaluate(self, security_id: SecurityId, as_of: date) -> RuleDecision:
        if not isinstance(security_id, SecurityId):
            raise TypeError("security_id must be a SecurityId")
        if type(as_of) is not date:
            raise TypeError("as_of must be a date, not a datetime")
        lifecycle = self._histories.get(security_id)
        if lifecycle is None:
            return RuleDecision.exclude(
                Exclusion(
                    ExclusionCode.MISSING_LISTING_HISTORY,
                    "listing",
                    "no listing lifecycle was supplied for the as-of query",
                )
            )
        status = lifecycle.status_as_of(as_of)
        if status is ListingStatus.PRE_LISTING:
            return RuleDecision.exclude(
                Exclusion(
                    ExclusionCode.PRE_LISTING,
                    "listing",
                    "security was not yet listed",
                    (("listing_date", lifecycle.listing_date.isoformat()),),
                )
            )
        if status is ListingStatus.DELISTED:
            assert lifecycle.delisting_date is not None
            return RuleDecision.exclude(
                Exclusion(
                    ExclusionCode.DELISTED,
                    "listing",
                    "security was already delisted",
                    (("delisting_date", lifecycle.delisting_date.isoformat()),),
                )
            )
        return RuleDecision.include()


@dataclass(frozen=True)
class STEligibilityPolicy:
    """Explicit versioned policy for special-treatment securities."""

    version: str
    allow_st: bool = False
    allow_star_st: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.version, str) or not self.version.strip():
            raise ValueError("ST policy version must be non-empty")


class HistoricalSTFilter:
    """ST eligibility using only supplied effective-dated histories."""

    def __init__(
        self,
        histories: Mapping[SecurityId, STStatusHistory],
        policy: STEligibilityPolicy,
    ) -> None:
        copied = dict(histories)
        if not isinstance(policy, STEligibilityPolicy):
            raise TypeError("policy must be STEligibilityPolicy")
        for security_id, history in copied.items():
            if not isinstance(security_id, SecurityId):
                raise TypeError("ST history keys must be SecurityId")
            if not isinstance(history, STStatusHistory):
                raise TypeError("ST histories must be STStatusHistory")
        self._histories = copied
        self.policy = policy

    def evaluate(self, security_id: SecurityId, as_of: date) -> RuleDecision:
        if type(as_of) is not date:
            raise TypeError("as_of must be a date, not a datetime")
        history = self._histories.get(security_id)
        if history is None:
            return self._unknown()
        try:
            status = history.as_of(as_of)
        except UnknownStatusError:
            return self._unknown()
        allowed = status is STStatus.NORMAL
        if status is STStatus.ST:
            allowed = self.policy.allow_st
        elif status is STStatus.STAR_ST:
            allowed = self.policy.allow_star_st
        if allowed:
            return RuleDecision.include()
        return RuleDecision.exclude(
            Exclusion(
                ExclusionCode.ST_STATUS,
                "st_status",
                "historical ST status is excluded by policy",
                (
                    ("policy_version", self.policy.version),
                    ("status", status.value),
                ),
            )
        )

    @staticmethod
    def _unknown() -> RuleDecision:
        return RuleDecision.exclude(
            Exclusion(
                ExclusionCode.MISSING_ST_HISTORY,
                "st_status",
                "no supplied ST fact covers the as-of date",
            )
        )


class HistoricalTradeStatusFilter:
    """As-of feasibility from status facts, separate from fill/valuation logic."""

    def __init__(
        self, histories: Mapping[SecurityId, TradeStatusHistory]
    ) -> None:
        copied = dict(histories)
        for security_id, history in copied.items():
            if not isinstance(security_id, SecurityId):
                raise TypeError("trade history keys must be SecurityId")
            if not isinstance(history, TradeStatusHistory):
                raise TypeError("trade histories must be TradeStatusHistory")
        self._histories = copied

    def evaluate(self, security_id: SecurityId, as_of: date) -> RuleDecision:
        if type(as_of) is not date:
            raise TypeError("as_of must be a date, not a datetime")
        history = self._histories.get(security_id)
        if history is None:
            return self._unknown()
        try:
            status = history.as_of(as_of)
        except UnknownStatusError:
            return self._unknown()
        if status is TradeStatus.TRADING:
            return RuleDecision.include()
        return RuleDecision.exclude(
            Exclusion(
                ExclusionCode.SUSPENDED,
                "trade_status",
                "security was suspended on the as-of date",
                (("status", status.value),),
            )
        )

    @staticmethod
    def _unknown() -> RuleDecision:
        return RuleDecision.exclude(
            Exclusion(
                ExclusionCode.MISSING_TRADE_STATUS_HISTORY,
                "trade_status",
                "no supplied trade-status fact covers the as-of date",
            )
        )
