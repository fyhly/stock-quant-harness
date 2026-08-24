"""Deterministic, non-repairing quality checks for daily bars."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import Enum
import hashlib
import json
from typing import Dict, Iterable, List, Optional, Tuple

from stock_quant.data.bars import DailyBar
from stock_quant.domain import SecurityId, TradingCalendar


class QualitySeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class QualityIssueCode(str, Enum):
    EMPTY_INPUT = "EMPTY_INPUT"
    MIXED_SECURITY = "MIXED_SECURITY"
    DUPLICATE_DATE = "DUPLICATE_DATE"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    MISSING_TRADING_DAY = "MISSING_TRADING_DAY"
    UNEXPECTED_NON_TRADING_DAY = "UNEXPECTED_NON_TRADING_DAY"
    OHLC_INVARIANT = "OHLC_INVARIANT"
    NEGATIVE_VOLUME_OR_AMOUNT = "NEGATIVE_VOLUME_OR_AMOUNT"
    EXTREME_CLOSE_RETURN = "EXTREME_CLOSE_RETURN"


@dataclass(frozen=True)
class QualityIssue:
    code: QualityIssueCode
    severity: QualitySeverity
    message: str
    security_id: Optional[SecurityId] = None
    trading_date: Optional[date] = None
    evidence: Tuple[Tuple[str, str], ...] = ()

    def canonical(self) -> Dict[str, object]:
        return {
            "code": self.code.value,
            "evidence": list(self.evidence),
            "message": self.message,
            "security_id": (
                str(self.security_id) if self.security_id is not None else None
            ),
            "severity": self.severity.value,
            "trading_date": (
                self.trading_date.isoformat()
                if self.trading_date is not None
                else None
            ),
        }


@dataclass(frozen=True)
class QualityReport:
    issues: Tuple[QualityIssue, ...]
    report_id: str

    @property
    def passed(self) -> bool:
        return not any(issue.severity is QualitySeverity.ERROR for issue in self.issues)

    @classmethod
    def from_issues(cls, issues: Iterable[QualityIssue]) -> "QualityReport":
        frozen = tuple(issues)
        payload = json.dumps(
            [issue.canonical() for issue in frozen],
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return cls(frozen, hashlib.sha256(payload).hexdigest())


def assess_daily_bars(
    bars: Iterable[DailyBar],
    *,
    calendar: Optional[TradingCalendar] = None,
    extreme_return_threshold: Decimal = Decimal("0.50"),
) -> QualityReport:
    """Report anomalies without sorting, dropping, filling, or mutating bars."""

    if (
        not isinstance(extreme_return_threshold, Decimal)
        or not extreme_return_threshold.is_finite()
        or extreme_return_threshold <= 0
    ):
        raise ValueError("extreme_return_threshold must be a positive Decimal")
    observations = tuple(bars)
    issues: List[QualityIssue] = []
    if not observations:
        issues.append(
            QualityIssue(
                QualityIssueCode.EMPTY_INPUT,
                QualitySeverity.WARNING,
                "no daily bars were supplied",
            )
        )
        return QualityReport.from_issues(issues)
    if any(not isinstance(bar, DailyBar) for bar in observations):
        raise TypeError("bars must contain DailyBar instances")

    first_security = observations[0].security_id
    seen = set()
    previous_key = None
    previous_by_security: Dict[SecurityId, DailyBar] = {}
    observed_dates = set()
    for bar in observations:
        day = bar.trading_day.value
        key = (str(bar.security_id), day)
        observed_dates.add(day)
        if bar.security_id != first_security:
            issues.append(
                QualityIssue(
                    QualityIssueCode.MIXED_SECURITY,
                    QualitySeverity.ERROR,
                    "input contains multiple securities",
                    bar.security_id,
                    day,
                )
            )
        if key in seen:
            issues.append(
                QualityIssue(
                    QualityIssueCode.DUPLICATE_DATE,
                    QualitySeverity.ERROR,
                    "duplicate security trading date",
                    bar.security_id,
                    day,
                )
            )
        seen.add(key)
        if previous_key is not None and key <= previous_key:
            issues.append(
                QualityIssue(
                    QualityIssueCode.OUT_OF_ORDER,
                    QualitySeverity.ERROR,
                    "bars are not strictly ordered by security and date",
                    bar.security_id,
                    day,
                )
            )
        previous_key = key
        _check_values(bar, issues)
        previous = previous_by_security.get(bar.security_id)
        if previous is not None:
            _check_extreme_return(previous, bar, extreme_return_threshold, issues)
        previous_by_security[bar.security_id] = bar

    if calendar is not None:
        start = min(observed_dates)
        end = max(observed_dates)
        expected = {
            day.value for day in calendar.trading_days if start <= day.value <= end
        }
        for missing in sorted(expected - observed_dates):
            issues.append(
                QualityIssue(
                    QualityIssueCode.MISSING_TRADING_DAY,
                    QualitySeverity.ERROR,
                    "expected injected-calendar trading date is missing",
                    first_security,
                    missing,
                )
            )
        for unexpected in sorted(observed_dates - expected):
            issues.append(
                QualityIssue(
                    QualityIssueCode.UNEXPECTED_NON_TRADING_DAY,
                    QualitySeverity.ERROR,
                    "bar date is not a trading day in the injected calendar",
                    first_security,
                    unexpected,
                )
            )
    return QualityReport.from_issues(issues)


def _check_values(bar: DailyBar, issues: List[QualityIssue]) -> None:
    values = (bar.open, bar.high, bar.low, bar.close)
    if (
        any(not isinstance(value, Decimal) or not value.is_finite() for value in values)
        or min(values) <= 0
        or bar.high < max(values)
        or bar.low > min(values)
    ):
        issues.append(
            QualityIssue(
                QualityIssueCode.OHLC_INVARIANT,
                QualitySeverity.ERROR,
                "OHLC values violate normalized schema invariants",
                bar.security_id,
                bar.trading_day.value,
            )
        )
    if (
        type(bar.volume) is not int
        or bar.volume < 0
        or not isinstance(bar.amount, Decimal)
        or not bar.amount.is_finite()
        or bar.amount < 0
    ):
        issues.append(
            QualityIssue(
                QualityIssueCode.NEGATIVE_VOLUME_OR_AMOUNT,
                QualitySeverity.ERROR,
                "volume or amount violates normalized schema invariants",
                bar.security_id,
                bar.trading_day.value,
            )
        )


def _check_extreme_return(
    previous: DailyBar,
    current: DailyBar,
    threshold: Decimal,
    issues: List[QualityIssue],
) -> None:
    try:
        change = abs(current.close / previous.close - Decimal(1))
    except (InvalidOperation, ZeroDivisionError):
        return
    if change > threshold:
        issues.append(
            QualityIssue(
                QualityIssueCode.EXTREME_CLOSE_RETURN,
                QualitySeverity.WARNING,
                "close-to-close return exceeds configured threshold",
                current.security_id,
                current.trading_day.value,
                (("absolute_return", str(change)), ("threshold", str(threshold))),
            )
        )
