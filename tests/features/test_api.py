from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from stock_quant.domain import Exchange, SecurityId, TradingDay
from stock_quant.features import (
    build_feature_result,
    FeatureContractError,
    FeatureObservation,
    FeatureRequest,
    FeatureScope,
)


SECURITY = SecurityId("600000", Exchange.SHANGHAI)
CUTOFF = datetime(2024, 1, 3, 14, tzinfo=timezone.utc)


def request() -> FeatureRequest:
    return FeatureRequest(
        "x", FeatureScope.TIME_SERIES, (SECURITY,), TradingDay(date(2024, 1, 3)), CUTOFF
    )


def row(available: datetime = CUTOFF) -> FeatureObservation:
    return FeatureObservation(
        SECURITY,
        datetime(2024, 1, 2, tzinfo=timezone.utc),
        available,
        Decimal("1"),
        "source",
    )


def test_contract_is_typed_ordered_and_deterministic() -> None:
    first = build_feature_result(
        request(), (row(),), formula_version="v1", lineage=("raw:a",)
    )
    assert first == build_feature_result(
        request(), (row(),), formula_version="v1", lineage=("raw:a",)
    )


def test_future_duplicate_and_missing_facts_fail_explicitly() -> None:
    with pytest.raises(FeatureContractError, match="unavailable"):
        build_feature_result(
            request(),
            (row(datetime(2024, 1, 3, 15, tzinfo=timezone.utc)),),
            formula_version="v1",
            lineage=("x",),
        )
    with pytest.raises(FeatureContractError, match="duplicate"):
        build_feature_result(
            request(), (row(), row()), formula_version="v1", lineage=("x",)
        )
    with pytest.raises(FeatureContractError, match="missing"):
        build_feature_result(request(), (), formula_version="v1", lineage=("x",))
