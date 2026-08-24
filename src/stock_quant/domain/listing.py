"""Immutable point-in-time security listing lifecycle."""

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional

from stock_quant.domain.security import SecurityId


class ListingStatus(str, Enum):
    """Listing state at an explicit as-of date."""

    PRE_LISTING = "PRE_LISTING"
    LISTED = "LISTED"
    DELISTED = "DELISTED"


@dataclass(frozen=True)
class ListingLifecycle:
    """Effective-dated lifecycle using ``[listing, delisting)`` semantics.

    ``delisting_date`` is the first date the security is no longer listed.
    Keeping this immutable object preserves queries about delisted securities.
    """

    security_id: SecurityId
    listing_date: date
    delisting_date: Optional[date] = None

    def __post_init__(self) -> None:
        if not isinstance(self.security_id, SecurityId):
            raise TypeError("security_id must be a SecurityId")
        if type(self.listing_date) is not date:
            raise TypeError("listing_date must be a date, not a datetime")
        if self.delisting_date is not None:
            if type(self.delisting_date) is not date:
                raise TypeError("delisting_date must be a date, not a datetime")
            if self.delisting_date <= self.listing_date:
                raise ValueError("delisting_date must be after listing_date")

    def status_as_of(self, as_of: date) -> ListingStatus:
        """Return lifecycle status using facts stored on this object."""

        if type(as_of) is not date:
            raise TypeError("as_of must be a date, not a datetime")
        if as_of < self.listing_date:
            return ListingStatus.PRE_LISTING
        if self.delisting_date is not None and as_of >= self.delisting_date:
            return ListingStatus.DELISTED
        return ListingStatus.LISTED

    def is_listed_as_of(self, as_of: date) -> bool:
        return self.status_as_of(as_of) is ListingStatus.LISTED
