from datetime import date, datetime
from decimal import Decimal

import pytest

from stock_quant.actions import BonusShareEvent, CashDividend, RightsIssue
from stock_quant.domain import Exchange, SecurityId


SECURITY = SecurityId("600000", Exchange.SHANGHAI)
SOURCE = "a" * 64


def test_event_types_have_distinct_availability_effect_and_credit_dates() -> None:
    cash = CashDividend(
        SECURITY, date(2024, 1, 1), date(2024, 5, 8), date(2024, 5, 9),
        date(2024, 5, 15), Decimal("0.30"), SOURCE, "v1"
    )
    bonus = BonusShareEvent(
        SECURITY, date(2024, 1, 1), date(2024, 5, 8), date(2024, 5, 9),
        date(2024, 5, 10), Decimal("0.1"), Decimal("0.2"), SOURCE, "v1"
    )
    rights = RightsIssue(
        SECURITY, date(2024, 1, 1), date(2024, 5, 8), date(2024, 5, 9),
        date(2024, 5, 20), Decimal("0.2"), Decimal("8.00"), SOURCE, "v1"
    )

    assert cash.announcement_date < cash.record_date < cash.ex_date < cash.pay_date
    assert bonus.ex_date < bonus.share_credit_date
    assert rights.ex_date < rights.settlement_date
    assert len({cash.event_id, bonus.event_id, rights.event_id}) == 3


def test_event_identity_is_deterministic_and_exact_decimal_is_significant() -> None:
    args = (
        SECURITY, date(2024, 1, 1), date(2024, 5, 8), date(2024, 5, 9),
        date(2024, 5, 15), Decimal("0.30"), SOURCE, "v1"
    )
    first = CashDividend(*args)
    second = CashDividend(*args)
    different = CashDividend(*args[:-3], Decimal("0.300"), SOURCE, "v1")

    assert first.event_id == second.event_id
    assert first.event_id != different.event_id


@pytest.mark.parametrize(
    "dates",
    [
        (date(2024, 2, 1), date(2024, 1, 1), date(2024, 3, 1)),
        (date(2024, 1, 1), date(2024, 2, 1), date(2024, 2, 1)),
    ],
)
def test_invalid_common_chronology_is_rejected(dates: tuple[date, date, date]) -> None:
    with pytest.raises(ValueError, match="announcement"):
        CashDividend(
            SECURITY, *dates, date(2024, 4, 1), Decimal("0.1"), SOURCE, "v1"
        )


def test_credit_dates_cannot_precede_ex_date() -> None:
    common = (SECURITY, date(2024, 1, 1), date(2024, 2, 1), date(2024, 2, 2))
    with pytest.raises(ValueError, match="pay_date"):
        CashDividend(*common, date(2024, 2, 1), Decimal("0.1"), SOURCE, "v1")
    with pytest.raises(ValueError, match="share_credit_date"):
        BonusShareEvent(
            *common, date(2024, 2, 1), Decimal("0.1"), Decimal(0), SOURCE, "v1"
        )
    with pytest.raises(ValueError, match="settlement_date"):
        RightsIssue(
            *common, date(2024, 2, 1), Decimal("0.1"), Decimal("8"), SOURCE, "v1"
        )


def test_decimal_and_datetime_boundaries_are_strict() -> None:
    with pytest.raises(TypeError, match="Decimal"):
        CashDividend(
            SECURITY, date(2024, 1, 1), date(2024, 2, 1), date(2024, 2, 2),
            date(2024, 2, 3), 0.1, SOURCE, "v1"  # type: ignore[arg-type]
        )
    with pytest.raises(TypeError, match="datetime"):
        CashDividend(
            SECURITY, datetime(2024, 1, 1), date(2024, 2, 1), date(2024, 2, 2),
            date(2024, 2, 3), Decimal("0.1"), SOURCE, "v1"
        )
