from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from stock_quant.domain import Exchange, SecurityId
from stock_quant.features import (
    FeatureContractError,
    quality_factors,
    StatementObservation,
)


SECURITY = SecurityId("600000", Exchange.SHANGHAI)
CUTOFF = datetime(2024, 5, 1, tzinfo=timezone.utc)
ORIGINAL = StatementObservation(
    SECURITY,
    date(2023, 12, 31),
    CUTOFF - timedelta(days=5),
    CUTOFF - timedelta(days=5),
    Decimal(10),
    Decimal(50),
    Decimal(100),
    Decimal(12),
    "original",
)


def test_aligned_formula_and_available_revision() -> None:
    revised = replace(
        ORIGINAL, revision_time=CUTOFF, net_income=Decimal(5), source_identity="revised"
    )
    result = quality_factors(
        (ORIGINAL, revised), security_id=SECURITY, decision_cutoff=CUTOFF
    )
    assert result.roe == Decimal("0.1")
    assert result.net_margin == Decimal("0.05")
    assert result.cash_flow_quality == Decimal("2.4")
    assert result.lineage == "revised"


def test_future_restatement_invalid_denominators_and_missing_fail() -> None:
    future = replace(ORIGINAL, revision_time=CUTOFF + timedelta(seconds=1))
    with pytest.raises(FeatureContractError, match="future"):
        quality_factors(
            (ORIGINAL, future), security_id=SECURITY, decision_cutoff=CUTOFF
        )
    invalid = replace(ORIGINAL, equity=Decimal(0), revenue=None, net_income=Decimal(-1))
    result = quality_factors((invalid,), security_id=SECURITY, decision_cutoff=CUTOFF)
    assert result.roe is None and result.net_margin is None
    assert result.cash_flow_quality is None
    with pytest.raises(FeatureContractError, match="missing"):
        quality_factors((), security_id=SECURITY, decision_cutoff=CUTOFF)
