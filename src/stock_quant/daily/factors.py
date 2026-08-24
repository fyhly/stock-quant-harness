"""Decision-cutoff-bounded daily factor snapshots with complete failures."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
from typing import Callable, Tuple

from stock_quant.daily.quality import DailyQualityEvidence, invoke_after_quality
from stock_quant.domain import SecurityId
from stock_quant.universe.snapshot import UniverseSnapshot


@dataclass(frozen=True)
class DailyFactorRow:
    security_id: SecurityId
    available_at: datetime
    values: Tuple[Tuple[str, Decimal], ...]


@dataclass(frozen=True)
class DailyFactorFailure:
    security_id: SecurityId
    failure_type: str
    failure_message: str


@dataclass(frozen=True)
class DailyFactorSnapshot:
    as_of: date
    decision_cutoff: datetime
    universe_identity: str
    config_identity: str
    lineage: Tuple[str, ...]
    rows: Tuple[DailyFactorRow, ...]
    failures: Tuple[DailyFactorFailure, ...]
    snapshot_identity: str


def refresh_daily_factors(
    evidence: DailyQualityEvidence,
    universe: UniverseSnapshot,
    *,
    decision_cutoff: datetime,
    config_identity: str,
    lineage: Tuple[str, ...],
    compute: Callable[[SecurityId, datetime], DailyFactorRow],
) -> DailyFactorSnapshot:
    if decision_cutoff.tzinfo is None or decision_cutoff.date() != universe.as_of:
        raise ValueError("decision cutoff must be timezone-aware on universe date")
    if len(config_identity) != 64 or not lineage:
        raise ValueError("factor config and lineage identities are required")

    def build() -> DailyFactorSnapshot:
        rows, failures = [], []
        for security in universe.included:
            try:
                row = compute(security, decision_cutoff)
                names = tuple(name for name, _ in row.values)
                if (
                    row.security_id != security
                    or row.available_at > decision_cutoff
                    or names != tuple(sorted(set(names)))
                    or not names
                    or any(not value.is_finite() for _, value in row.values)
                ):
                    raise ValueError("factor row violates cutoff/alignment contract")
                rows.append(row)
            except Exception as exc:
                failures.append(
                    DailyFactorFailure(security, type(exc).__name__, str(exc))
                )
        payload = {
            "as_of": universe.as_of.isoformat(),
            "cutoff": decision_cutoff.isoformat(),
            "universe": universe.snapshot_id,
            "config": config_identity,
            "lineage": lineage,
            "rows": [
                (
                    str(row.security_id),
                    row.available_at.isoformat(),
                    tuple((name, str(value)) for name, value in row.values),
                )
                for row in rows
            ],
            "failures": [
                (str(item.security_id), item.failure_type, item.failure_message)
                for item in failures
            ],
        }
        identity = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return DailyFactorSnapshot(
            universe.as_of,
            decision_cutoff,
            universe.snapshot_id,
            config_identity,
            lineage,
            tuple(rows),
            tuple(failures),
            identity,
        )

    return invoke_after_quality(evidence, build)
