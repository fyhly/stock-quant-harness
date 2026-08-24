from datetime import date
from decimal import Decimal

import pytest

from stock_quant.domain import SecurityId
from stock_quant.market_research.exposure import (
    ExposureAnalyticsError,
    ExposurePoint,
    exposure_attribution,
)
from stock_quant.universe import (
    IndustryMembership,
    IndustryMembershipHistory,
    IndustryTaxonomy,
)
from stock_quant.universe.snapshot import UniverseSnapshot


A, B = SecurityId.parse("000001.XSHE"), SecurityId.parse("600000.XSHG")
TAXONOMY = IndustryTaxonomy("CITICS", "v1")


def snap(day: date) -> UniverseSnapshot:
    return UniverseSnapshot(
        "a" * 64, day, (A, B), (), "v1", ("b" * 64,), "c" * 64, "d" * 64
    )


def test_sector_changes_are_pit_and_attribution_reconciles() -> None:
    history = IndustryMembershipHistory(
        TAXONOMY,
        (
            IndustryMembership(TAXONOMY, A, "OLD", date(2020, 1, 1), date(2024, 1, 3)),
            IndustryMembership(TAXONOMY, A, "NEW", date(2024, 1, 3)),
            IndustryMembership(TAXONOMY, B, "BANK", date(2020, 1, 1)),
        ),
    )
    points = (
        ExposurePoint(A, Decimal(".5"), Decimal(".1"), (("value", Decimal(1)),)),
        ExposurePoint(B, Decimal(".5"), Decimal(".2"), (("value", Decimal(0)),)),
    )
    result = exposure_attribution(
        snap(date(2024, 1, 2)),
        history,
        points,
        style_model_identity="e" * 64,
        style_returns={"value": Decimal(".02")},
    )
    assert result.sector_contributions == (
        ("BANK", Decimal(".10")),
        ("OLD", Decimal(".05")),
    )
    assert (
        sum((value for _, value in result.sector_contributions), Decimal(0))
        == result.total_return
    )
    assert (
        result.residual_return == Decimal(".14")
        and result.taxonomy_identity == "CITICS:v1"
    )


def test_gap_and_incomplete_pit_universe_fail_instead_of_current_backfill() -> None:
    history = IndustryMembershipHistory(
        TAXONOMY,
        (
            IndustryMembership(TAXONOMY, A, "NEW", date(2024, 1, 3)),
            IndustryMembership(TAXONOMY, B, "BANK", date(2020, 1, 1)),
        ),
    )
    with pytest.raises(ExposureAnalyticsError, match="missing PIT"):
        exposure_attribution(
            snap(date(2024, 1, 2)),
            history,
            (
                ExposurePoint(A, Decimal(1), Decimal(0), ()),
                ExposurePoint(B, Decimal(0), Decimal(0), ()),
            ),
            style_model_identity="e" * 64,
            style_returns={},
        )
    with pytest.raises(ExposureAnalyticsError, match="exactly cover"):
        exposure_attribution(
            snap(date(2024, 1, 2)),
            history,
            (),
            style_model_identity="e" * 64,
            style_returns={},
        )
