from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Tuple

from stock_quant.daily.candidates import (
    DailyCandidateSnapshot,
    generate_daily_candidates,
)
from stock_quant.daily.factors import (
    DailyFactorFailure,
    DailyFactorRow,
    DailyFactorSnapshot,
)
from stock_quant.domain import SecurityId


A, B, C, D = (
    SecurityId.parse("000001.XSHE"),
    SecurityId.parse("000002.XSHE"),
    SecurityId.parse("600000.XSHG"),
    SecurityId.parse("600001.XSHG"),
)
NOW = datetime(2024, 1, 2, 7, tzinfo=timezone.utc)


def snapshot(order: Tuple[Tuple[SecurityId, Decimal], ...]) -> DailyFactorSnapshot:
    rows = tuple(
        DailyFactorRow(security, NOW, (("score", value),)) for security, value in order
    )
    return DailyFactorSnapshot(
        date(2024, 1, 2),
        NOW,
        "a" * 64,
        "b" * 64,
        ("c" * 64,),
        rows,
        (DailyFactorFailure(D, "Missing", "visible"),),
        "d" * 64,
    )


def test_ranking_ties_filters_reasons_input_order_and_no_silent_drop() -> None:
    order = ((C, Decimal(1)), (B, Decimal(2)), (A, Decimal(2)))

    def build(source: Tuple[Tuple[SecurityId, Decimal], ...]) -> DailyCandidateSnapshot:
        return generate_daily_candidates(
            snapshot(source),
            top_n=1,
            config_identity="e" * 64,
            score=lambda row: row.values[0][1],
            filters=lambda row: ("LIQUIDITY_FILTER",) if row.security_id == C else (),
        )

    first, second = build(order), build(tuple(reversed(order)))
    assert first.candidates == second.candidates
    by_id = {item.security_id: item for item in first.candidates}
    assert first.selected == (A,) and by_id[A].rank == 1 and by_id[B].rank == 2
    assert by_id[B].reasons == ("BELOW_TOP_N",)
    assert by_id[C].reasons == ("LIQUIDITY_FILTER",)
    assert "FACTOR_FAILURE" in by_id[D].reasons[0] and len(by_id) == 4


def test_scoring_failure_is_visible_not_dropped() -> None:
    result = generate_daily_candidates(
        snapshot(((A, Decimal(1)),)),
        top_n=1,
        config_identity="e" * 64,
        score=lambda _row: Decimal("NaN"),
        filters=lambda _row: (),
    )
    assert not result.selected and "SCORING_FAILURE" in result.candidates[0].reasons[0]
