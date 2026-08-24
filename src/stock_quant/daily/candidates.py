"""Complete explainable daily candidate ranking with no silent drops."""

from dataclasses import dataclass
from decimal import Decimal
import hashlib
import json
from typing import Callable, Optional, Tuple

from stock_quant.daily.factors import DailyFactorRow, DailyFactorSnapshot
from stock_quant.domain import SecurityId


@dataclass(frozen=True)
class DailyCandidate:
    security_id: SecurityId
    score: Optional[Decimal]
    rank: Optional[int]
    included: bool
    reasons: Tuple[str, ...]


@dataclass(frozen=True)
class DailyCandidateSnapshot:
    factor_identity: str
    config_identity: str
    candidates: Tuple[DailyCandidate, ...]
    selected: Tuple[SecurityId, ...]
    snapshot_identity: str


def generate_daily_candidates(
    factors: DailyFactorSnapshot,
    *,
    top_n: int,
    config_identity: str,
    score: Callable[[DailyFactorRow], Decimal],
    filters: Callable[[DailyFactorRow], Tuple[str, ...]],
) -> DailyCandidateSnapshot:
    if top_n <= 0 or len(config_identity) != 64:
        raise ValueError("invalid candidate configuration")
    failures = {item.security_id: item for item in factors.failures}
    scored = []
    records = []
    for row in factors.rows:
        try:
            value = score(row)
            if not value.is_finite():
                raise ValueError("candidate score is not finite")
            reasons = tuple(sorted(set(filters(row))))
            if reasons:
                records.append(
                    DailyCandidate(row.security_id, value, None, False, reasons)
                )
            else:
                scored.append((row.security_id, value))
        except Exception as exc:
            records.append(
                DailyCandidate(
                    row.security_id,
                    None,
                    None,
                    False,
                    (f"SCORING_FAILURE:{type(exc).__name__}:{exc}",),
                )
            )
    ranked = tuple(sorted(scored, key=lambda item: (-item[1], item[0])))
    for index, (security, value) in enumerate(ranked, 1):
        included = index <= top_n
        records.append(
            DailyCandidate(
                security, value, index, included, () if included else ("BELOW_TOP_N",)
            )
        )
    for security, failure in failures.items():
        records.append(
            DailyCandidate(
                security,
                None,
                None,
                False,
                (f"FACTOR_FAILURE:{failure.failure_type}:{failure.failure_message}",),
            )
        )
    records_tuple = tuple(sorted(records, key=lambda item: item.security_id))
    expected = {row.security_id for row in factors.rows} | set(failures)
    if {item.security_id for item in records_tuple} != expected or len(
        records_tuple
    ) != len(expected):
        raise ValueError("candidate evidence does not reconcile to factor universe")
    selected = tuple(item.security_id for item in records_tuple if item.included)
    payload = [
        (str(item.security_id), str(item.score), item.rank, item.included, item.reasons)
        for item in records_tuple
    ]
    identity = hashlib.sha256(
        json.dumps(
            {
                "factor": factors.snapshot_identity,
                "config": config_identity,
                "candidates": payload,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    return DailyCandidateSnapshot(
        factors.snapshot_identity, config_identity, records_tuple, selected, identity
    )
