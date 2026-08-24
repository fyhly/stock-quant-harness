"""Explainable point-in-time eligibility rule results."""

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Mapping, Optional, Tuple

from stock_quant.domain import ListingLifecycle, ListingStatus, SecurityId


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
