"""Unambiguous A-share security identifiers."""

from dataclasses import dataclass
from enum import Enum
import re
from typing import ClassVar, Dict, Tuple


class Exchange(str, Enum):
    """Supported exchanges, represented by their ISO 10383 MIC."""

    SHANGHAI = "XSHG"
    SHENZHEN = "XSHE"


class MarketSegment(str, Enum):
    """Supported A-share market segments."""

    MAIN_BOARD = "MAIN_BOARD"
    STAR_MARKET = "STAR_MARKET"
    CHINEXT = "CHINEXT"


@dataclass(frozen=True, order=True)
class SecurityId:
    """Provider-independent six-digit A-share code plus explicit exchange."""

    code: str
    exchange: Exchange

    _CODE_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^[0-9]{6}$")
    _PREFIXES: ClassVar[Dict[Exchange, Tuple[Tuple[str, MarketSegment], ...]]] = {
        Exchange.SHANGHAI: (
            ("600", MarketSegment.MAIN_BOARD),
            ("601", MarketSegment.MAIN_BOARD),
            ("603", MarketSegment.MAIN_BOARD),
            ("605", MarketSegment.MAIN_BOARD),
            ("688", MarketSegment.STAR_MARKET),
            ("689", MarketSegment.STAR_MARKET),
        ),
        Exchange.SHENZHEN: (
            ("000", MarketSegment.MAIN_BOARD),
            ("001", MarketSegment.MAIN_BOARD),
            ("002", MarketSegment.MAIN_BOARD),
            ("003", MarketSegment.MAIN_BOARD),
            ("300", MarketSegment.CHINEXT),
            ("301", MarketSegment.CHINEXT),
        ),
    }

    def __post_init__(self) -> None:
        if not isinstance(self.exchange, Exchange):
            raise TypeError("exchange must be an Exchange")
        if not self._CODE_PATTERN.fullmatch(self.code):
            raise ValueError("security code must contain exactly six ASCII digits")
        self._segment_for(self.code, self.exchange)

    @property
    def market_segment(self) -> MarketSegment:
        """Return the segment implied by the validated code and exchange."""

        return self._segment_for(self.code, self.exchange)

    @classmethod
    def parse(cls, value: str) -> "SecurityId":
        """Parse canonical ``CODE.MIC`` form without guessing an exchange."""

        parts = value.split(".")
        if len(parts) != 2:
            raise ValueError("security identifier must use canonical CODE.MIC form")
        code, raw_exchange = parts
        try:
            exchange = Exchange(raw_exchange)
        except ValueError as exc:
            raise ValueError(f"unsupported exchange MIC: {raw_exchange!r}") from exc
        return cls(code=code, exchange=exchange)

    def __str__(self) -> str:
        return f"{self.code}.{self.exchange.value}"

    @classmethod
    def _segment_for(cls, code: str, exchange: Exchange) -> MarketSegment:
        for prefix, segment in cls._PREFIXES[exchange]:
            if code.startswith(prefix):
                return segment
        raise ValueError(
            f"code {code!r} is not an explicitly supported A-share code "
            f"for {exchange.value}"
        )
