"""As-of-neutral registry retaining every known security identity."""

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Tuple

from stock_quant.domain import MarketSegment, SecurityId


class DuplicateSecurityError(ValueError):
    """Raised when identical metadata is supplied more than once."""


class ConflictingSecurityMetadataError(ValueError):
    """Raised when one SecurityId has conflicting identity metadata."""


class UnknownSecurityError(KeyError):
    """Raised when an identity is absent from the master."""


@dataclass(frozen=True, order=True)
class SecurityMetadata:
    """Stable identity metadata; lifecycle and current state live elsewhere."""

    security_id: SecurityId
    display_name: str

    def __post_init__(self) -> None:
        if not isinstance(self.security_id, SecurityId):
            raise TypeError("security_id must be a SecurityId")
        if not isinstance(self.display_name, str) or not self.display_name.strip():
            raise ValueError("display_name must be a non-empty string")
        if self.display_name != self.display_name.strip():
            raise ValueError("display_name cannot contain surrounding whitespace")

    @property
    def market_segment(self) -> MarketSegment:
        return self.security_id.market_segment


class SecurityMaster:
    """Immutable deterministic registry that never filters historical failures."""

    def __init__(self, securities: Iterable[SecurityMetadata]) -> None:
        by_id: Dict[SecurityId, SecurityMetadata] = {}
        for metadata in securities:
            if not isinstance(metadata, SecurityMetadata):
                raise TypeError("master entries must be SecurityMetadata")
            existing = by_id.get(metadata.security_id)
            if existing is not None:
                if existing == metadata:
                    raise DuplicateSecurityError(
                        f"duplicate metadata for {metadata.security_id}"
                    )
                raise ConflictingSecurityMetadataError(
                    f"conflicting metadata for {metadata.security_id}"
                )
            by_id[metadata.security_id] = metadata
        self._by_id: Mapping[SecurityId, SecurityMetadata] = by_id
        self._securities = tuple(sorted(by_id.values()))

    @property
    def securities(self) -> Tuple[SecurityMetadata, ...]:
        return self._securities

    def get(self, security_id: SecurityId) -> SecurityMetadata:
        if not isinstance(security_id, SecurityId):
            raise TypeError("security_id must be a SecurityId")
        try:
            return self._by_id[security_id]
        except KeyError as exc:
            raise UnknownSecurityError(str(security_id)) from exc
