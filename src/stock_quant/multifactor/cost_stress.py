"""Predeclared complete and monotonic multi-level cost sensitivity."""

from dataclasses import dataclass
from decimal import Decimal
from html import escape
from typing import Mapping, Optional, Tuple, cast


class CostStressError(ValueError):
    pass


@dataclass(frozen=True, order=True)
class CostLevel:
    level_id: str
    commission_rate: Decimal
    tax_rate: Decimal
    slippage_rate: Decimal

    @property
    def total_rate(self) -> Decimal:
        return self.commission_rate + self.tax_rate + self.slippage_rate


@dataclass(frozen=True)
class CostStressRecord:
    level: CostLevel
    turnover: Decimal
    gross_return: Decimal
    total_cost: Optional[Decimal]
    net_return: Optional[Decimal]
    succeeded: bool
    failure_message: str
    convention: str = "ALL_RATES_TIMES_ONE_WAY_TURNOVER"


@dataclass(frozen=True)
class CostStressResult:
    records: Tuple[CostStressRecord, ...]
    total_levels: int
    successful_levels: int
    failed_levels: int


def cost_stress(
    gross_return: Decimal,
    turnover: Decimal,
    levels: Tuple[CostLevel, ...],
    *,
    failures: Optional[Mapping[str, str]] = None,
) -> CostStressResult:
    retained_failures = dict(failures or {})
    ordered = tuple(sorted(levels, key=lambda item: (item.total_rate, item.level_id)))
    ids = tuple(item.level_id for item in ordered)
    if (
        not ordered
        or len(set(ids)) != len(ids)
        or set(retained_failures) - set(ids)
        or not gross_return.is_finite()
        or not turnover.is_finite()
        or turnover < 0
    ):
        raise CostStressError("invalid or incomplete predefined cost space")
    records = []
    for level in ordered:
        rates = (level.commission_rate, level.tax_rate, level.slippage_rate)
        if not level.level_id or any(
            not rate.is_finite() or rate < 0 for rate in rates
        ):
            raise CostStressError("cost rates must be nonnegative finite")
        failure = retained_failures.get(level.level_id, "")
        if failure:
            records.append(
                CostStressRecord(
                    level, turnover, gross_return, None, None, False, failure
                )
            )
        else:
            total_cost = turnover * level.total_rate
            records.append(
                CostStressRecord(
                    level,
                    turnover,
                    gross_return,
                    total_cost,
                    gross_return - total_cost,
                    True,
                    "",
                )
            )
    succeeded = sum(record.succeeded for record in records)
    successful_nets = [
        cast(Decimal, record.net_return) for record in records if record.succeeded
    ]
    if any(left < right for left, right in zip(successful_nets, successful_nets[1:])):
        raise CostStressError("net returns must be monotonic under identical fills")
    return CostStressResult(
        tuple(records), len(records), succeeded, len(records) - succeeded
    )


def render_cost_stress_report(result: CostStressResult) -> str:
    if result.total_levels != result.successful_levels + result.failed_levels:
        raise CostStressError("cost level totals do not reconcile")
    rows = "".join(
        "<tr>"
        + "".join(
            f"<td>{escape(value)}</td>"
            for value in (
                record.level.level_id,
                str(record.turnover),
                str(record.gross_return),
                str(record.total_cost),
                str(record.net_return),
                record.failure_message,
            )
        )
        + "</tr>"
        for record in result.records
    )
    return (
        '<!doctype html><html><head><meta charset="utf-8"><title>Cost stress</title>'
        "</head><body><h1>Multi-factor cost stress</h1><strong>RESEARCH ONLY</strong>"
        f"<p>Total: {result.total_levels}; succeeded: {result.successful_levels}; "
        f"failed: {result.failed_levels}</p><table>{rows}</table></body></html>"
    )
