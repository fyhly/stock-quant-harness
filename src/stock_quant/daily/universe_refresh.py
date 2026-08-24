"""Daily PIT universe snapshot from quality-approved local inputs."""

from datetime import date
from typing import Callable, Iterable

from stock_quant.daily.quality import DailyQualityEvidence, invoke_after_quality
from stock_quant.universe.engine import UniverseResult
from stock_quant.universe.snapshot import UniverseSnapshot, create_universe_snapshot


def refresh_daily_universe(
    evidence: DailyQualityEvidence,
    *,
    as_of: date,
    build_pit: Callable[[date], UniverseResult],
    local_data_identities: Iterable[str],
    code_identity: str,
    config_identity: str,
) -> UniverseSnapshot:
    identities = tuple(sorted(local_data_identities))
    if not identities or any(len(item) != 64 for item in identities):
        raise ValueError("validated local data identities are required")

    def build() -> UniverseSnapshot:
        result = build_pit(as_of)
        if result.as_of != as_of:
            raise ValueError("PIT universe result date mismatch")
        return create_universe_snapshot(
            result,
            upstream_identities=identities,
            code_identity=code_identity,
            config_identity=config_identity,
        )

    return invoke_after_quality(evidence, build)
