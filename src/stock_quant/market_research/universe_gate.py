"""Coverage and quality gate over immutable PIT universe snapshots."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping, Tuple

from stock_quant.domain import SecurityId
from stock_quant.universe.snapshot import UniverseSnapshot


class MarketUniverseGateError(ValueError):
    pass


@dataclass(frozen=True)
class MarketUniverseGateEvidence:
    snapshot_id: str
    as_of: str
    passed: bool
    eligible_count: int
    good_count: int
    coverage: Decimal
    reasons: Tuple[Tuple[str, str], ...]


def evaluate_market_universe(
    snapshot: UniverseSnapshot,
    quality: Mapping[SecurityId, bool],
    *,
    minimum_securities: int,
    minimum_coverage: Decimal,
) -> MarketUniverseGateEvidence:
    if minimum_securities <= 0 or not Decimal(0) <= minimum_coverage <= Decimal(1):
        raise MarketUniverseGateError("invalid market gate thresholds")
    eligible = snapshot.included
    eligible_set = set(eligible)
    if any(security not in eligible_set for security in quality):
        raise MarketUniverseGateError("quality contains non-PIT-universe securities")
    reasons = []
    good = 0
    for security in eligible:
        state = quality.get(security)
        if state is None:
            reasons.append((str(security), "MISSING_SAMPLE"))
        elif not state:
            reasons.append((str(security), "BAD_QUALITY"))
        else:
            good += 1
    coverage = Decimal(good) / Decimal(len(eligible)) if eligible else Decimal(0)
    if len(eligible) < minimum_securities:
        reasons.append(("*", "MINIMUM_SECURITY_COUNT"))
    if coverage < minimum_coverage:
        reasons.append(("*", "MINIMUM_COVERAGE"))
    return MarketUniverseGateEvidence(
        snapshot.snapshot_id,
        snapshot.as_of.isoformat(),
        not reasons,
        len(eligible),
        good,
        coverage,
        tuple(sorted(reasons)),
    )
