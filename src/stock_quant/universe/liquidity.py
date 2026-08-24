"""Historical liquidity eligibility using a strict pre-decision window."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

from stock_quant.data import DailyBarSeries
from stock_quant.domain import CalendarRangeError, SecurityId, TradingCalendar
from stock_quant.universe.rules import Exclusion, ExclusionCode, RuleDecision


@dataclass(frozen=True)
class LiquidityPolicy:
    version: str
    window_sessions: int
    min_average_volume: Decimal
    min_average_amount: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.version, str) or not self.version.strip():
            raise ValueError("liquidity policy version must be non-empty")
        if type(self.window_sessions) is not int or self.window_sessions <= 0:
            raise ValueError("window_sessions must be a positive integer")
        for name in ("min_average_volume", "min_average_amount"):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise ValueError(f"{name} must be a nonnegative finite Decimal")


class HistoricalLiquidityFilter:
    """Fail-closed trailing liquidity using bars strictly before cutoff."""

    def __init__(
        self, calendar: TradingCalendar, policy: LiquidityPolicy
    ) -> None:
        if not isinstance(calendar, TradingCalendar):
            raise TypeError("calendar must be a TradingCalendar")
        if not isinstance(policy, LiquidityPolicy):
            raise TypeError("policy must be a LiquidityPolicy")
        self.calendar = calendar
        self.policy = policy

    def evaluate(
        self,
        security_id: SecurityId,
        series: Optional[DailyBarSeries],
        decision_date: date,
    ) -> RuleDecision:
        if type(decision_date) is not date:
            raise TypeError("decision_date must be a date, not a datetime")
        try:
            self.calendar.is_trading_day(decision_date)
        except CalendarRangeError:
            return self._missing("decision date is outside calendar coverage")
        if series is None:
            return self._missing("no DailyBarSeries was supplied")
        if not isinstance(series, DailyBarSeries):
            raise TypeError("series must be a DailyBarSeries or None")
        if series.security_id != security_id:
            raise ValueError("liquidity series identity mismatch")
        future_dates = tuple(
            bar.trading_day.value
            for bar in series.bars
            if bar.trading_day.value >= decision_date
        )
        if future_dates:
            return RuleDecision.exclude(
                Exclusion(
                    ExclusionCode.FUTURE_LIQUIDITY_DATA,
                    "liquidity",
                    "series contains a decision-date or future bar",
                    (("first_rejected_date", future_dates[0].isoformat()),),
                )
            )

        available_days = tuple(
            day.value
            for day in self.calendar.trading_days
            if day.value < decision_date
        )
        expected = available_days[-self.policy.window_sessions :]
        if len(expected) != self.policy.window_sessions:
            return self._missing("calendar has insufficient pre-decision history")
        by_date = {bar.trading_day.value: bar for bar in series.bars}
        missing = tuple(day for day in expected if day not in by_date)
        unexpected = tuple(
            sorted(
                day
                for day in by_date
                if expected[0] <= day < decision_date and day not in set(expected)
            )
        )
        if missing or unexpected:
            missing_evidence = (
                ("missing_dates", ",".join(day.isoformat() for day in missing)),
                ("unexpected_dates", ",".join(day.isoformat() for day in unexpected)),
            )
            return self._missing(
                "liquidity window is gapped or off-calendar", missing_evidence
            )
        window = tuple(by_date[day] for day in expected)
        average_volume = sum(Decimal(bar.volume) for bar in window) / Decimal(
            len(window)
        )
        average_amount = sum((bar.amount for bar in window), Decimal(0)) / Decimal(
            len(window)
        )
        evidence = (
            ("average_amount", str(average_amount)),
            ("average_volume", str(average_volume)),
            ("policy_version", self.policy.version),
            ("window_end", expected[-1].isoformat()),
            ("window_sessions", str(len(window))),
            ("window_start", expected[0].isoformat()),
        )
        if (
            average_volume < self.policy.min_average_volume
            or average_amount < self.policy.min_average_amount
        ):
            return RuleDecision.exclude(
                Exclusion(
                    ExclusionCode.INSUFFICIENT_LIQUIDITY,
                    "liquidity",
                    "trailing liquidity is below configured thresholds",
                    evidence,
                )
            )
        return RuleDecision.include()

    @staticmethod
    def _missing(
        message: str, evidence: tuple[tuple[str, str], ...] = ()
    ) -> RuleDecision:
        return RuleDecision.exclude(
            Exclusion(
                ExclusionCode.MISSING_LIQUIDITY_HISTORY,
                "liquidity",
                message,
                evidence,
            )
        )
