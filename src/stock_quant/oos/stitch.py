"""Continuous OOS return stitching with explicit cash and boundary rules."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable, Tuple

from stock_quant.oos.windows import TimeWindow


class StitchError(ValueError):
    pass


@dataclass(frozen=True, order=True)
class OOSReturnPoint:
    day: date
    simple_return: Decimal


@dataclass(frozen=True)
class OOSReturnSegment:
    window_identity: str
    window: TimeWindow
    points: Tuple[OOSReturnPoint, ...]


@dataclass(frozen=True)
class StitchedEquityPoint:
    day: date
    simple_return: Decimal
    equity: Decimal
    window_identity: str


@dataclass(frozen=True)
class StitchedOOSResult:
    initial_cash: Decimal
    final_equity: Decimal
    points: Tuple[StitchedEquityPoint, ...]
    convention: str = "HALF_OPEN_WINDOWS;RETURN_APPLIED_TO_PRIOR_CLOSE_CASH"


def stitch_oos_results(
    segments: Iterable[OOSReturnSegment],
    expected_dates: Tuple[date, ...],
    *,
    initial_cash: Decimal,
) -> StitchedOOSResult:
    if initial_cash <= 0 or not initial_cash.is_finite():
        raise StitchError("initial cash must be positive finite")
    ordered = tuple(segments)
    if tuple(sorted(ordered, key=lambda item: item.window.start)) != ordered:
        raise StitchError("segments must be ordered")
    raw_points = []
    previous_end = None
    for segment in ordered:
        if previous_end is not None and previous_end > segment.window.start:
            raise StitchError("OOS segment windows overlap")
        previous_end = segment.window.end
        if tuple(sorted(segment.points)) != segment.points:
            raise StitchError("segment points must be ordered")
        for point in segment.points:
            if (
                not segment.window.contains(point.day)
                or not point.simple_return.is_finite()
                or point.simple_return <= -1
            ):
                raise StitchError("invalid or out-of-window return point")
            raw_points.append((point, segment.window_identity))
    dates = tuple(point.day for point, _ in raw_points)
    if len(set(dates)) != len(dates):
        raise StitchError("duplicate OOS dates")
    if dates != expected_dates:
        raise StitchError("OOS dates contain a gap or unexpected date")
    equity = initial_cash
    output = []
    for point, identity in raw_points:
        equity *= Decimal(1) + point.simple_return
        output.append(
            StitchedEquityPoint(point.day, point.simple_return, equity, identity)
        )
    return StitchedOOSResult(initial_cash, equity, tuple(output))
