"""Complete stability summaries retaining failures and negative windows."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, Optional, Tuple


class StabilityError(ValueError):
    pass


@dataclass(frozen=True)
class StabilityWindow:
    window_identity: str
    parameter_identity: str
    oos_return: Optional[Decimal]
    factor_values: Tuple[Tuple[str, Decimal], ...]
    failure_stage: str = ""
    failure_message: str = ""


@dataclass(frozen=True)
class StabilitySummary:
    total_windows: int
    successful_windows: int
    failed_windows: int
    negative_windows: int
    mean_oos_return: Decimal
    minimum_oos_return: Decimal
    maximum_oos_return: Decimal
    parameter_counts: Tuple[Tuple[str, int], ...]
    factor_means: Tuple[Tuple[str, Decimal], ...]
    failures: Tuple[Tuple[str, str, str], ...]


def stability_summary(windows: Iterable[StabilityWindow]) -> StabilitySummary:
    rows = tuple(windows)
    if not rows or len({row.window_identity for row in rows}) != len(rows):
        raise StabilityError("stability requires unique, nonempty windows")
    successes, failures = [], []
    parameter_counts: dict[str, int] = {}
    factor_totals: dict[str, tuple[Decimal, int]] = {}
    for row in rows:
        if row.oos_return is None:
            if not row.failure_stage:
                raise StabilityError("missing window result requires failure evidence")
            failures.append(
                (row.window_identity, row.failure_stage, row.failure_message)
            )
            continue
        if row.failure_stage or not row.oos_return.is_finite():
            raise StabilityError("successful window result is invalid")
        successes.append(row.oos_return)
        parameter_counts[row.parameter_identity] = (
            parameter_counts.get(row.parameter_identity, 0) + 1
        )
        names = tuple(name for name, _ in row.factor_values)
        if names != tuple(sorted(set(names))):
            raise StabilityError("factor values must be sorted and unique")
        for name, value in row.factor_values:
            if not value.is_finite():
                raise StabilityError("factor values must be finite")
            total, count = factor_totals.get(name, (Decimal(0), 0))
            factor_totals[name] = (total + value, count + 1)
    if not successes:
        zero = Decimal(0)
        minimum = maximum = zero
    else:
        zero = sum(successes, Decimal(0)) / Decimal(len(successes))
        minimum, maximum = min(successes), max(successes)
    factor_means = tuple(
        sorted(
            (name, total / Decimal(count))
            for name, (total, count) in factor_totals.items()
        )
    )
    return StabilitySummary(
        len(rows),
        len(successes),
        len(failures),
        sum(value < 0 for value in successes),
        zero,
        minimum,
        maximum,
        tuple(sorted(parameter_counts.items())),
        factor_means,
        tuple(sorted(failures)),
    )
