from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import pytest
from stock_quant.benchmark import run_quality_benchmark
from stock_quant.domain import Exchange, SecurityId
from stock_quant.features import FeatureContractError, StatementObservation


def test_quality_announcement_restatement_and_deterministic_rank() -> None:
    ids = (
        SecurityId("600000", Exchange.SHANGHAI),
        SecurityId("600001", Exchange.SHANGHAI),
    )
    cutoff = datetime(2024, 5, 1, tzinfo=timezone.utc)
    rows = tuple(
        StatementObservation(
            sid,
            date(2023, 12, 31),
            cutoff - timedelta(days=1),
            cutoff - timedelta(days=1),
            Decimal(10 - index),
            Decimal(50),
            Decimal(100),
            Decimal(12),
            f"s{index}",
        )
        for index, sid in enumerate(ids)
    )
    first = run_quality_benchmark(rows, ids, decision_cutoff=cutoff)
    assert first == run_quality_benchmark(
        reversed(rows), reversed(ids), decision_cutoff=cutoff
    )
    assert first.ranked[0][0] == ids[0] and first.metric == "roe"
    revised = replace(
        rows[0], revision_time=cutoff, net_income=Decimal(1), source_identity="revision"
    )
    assert (
        run_quality_benchmark(
            (rows[0], revised, rows[1]), ids, decision_cutoff=cutoff
        ).ranked[0][0]
        == ids[1]
    )
    with pytest.raises(FeatureContractError, match="future"):
        run_quality_benchmark(
            (replace(rows[0], revision_time=cutoff + timedelta(seconds=1)), rows[1]),
            ids,
            decision_cutoff=cutoff,
        )
