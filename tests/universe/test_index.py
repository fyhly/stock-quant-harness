from datetime import date

import pytest

from stock_quant.domain import Exchange, SecurityId
from stock_quant.universe import (
    IndexId,
    IndexMembership,
    IndexMembershipHistory,
    UnknownIndexHistoryError,
)


INDEX = IndexId("000300.XSHG")
FIRST = SecurityId("600000", Exchange.SHANGHAI)
SECOND = SecurityId("000001", Exchange.SHENZHEN)


def test_entry_exit_gap_and_deterministic_members() -> None:
    history = IndexMembershipHistory(
        INDEX,
        [
            IndexMembership(INDEX, SECOND, date(2020, 1, 1)),
            IndexMembership(INDEX, FIRST, date(2010, 1, 1), date(2015, 1, 1)),
            IndexMembership(INDEX, FIRST, date(2016, 1, 1), date(2019, 1, 1)),
        ],
        coverage_start=date(2010, 1, 1),
        coverage_end=date(2025, 1, 1),
    )

    assert history.is_member(FIRST, date(2010, 1, 1))
    assert not history.is_member(FIRST, date(2015, 1, 1))
    assert not history.is_member(FIRST, date(2015, 6, 1))
    assert history.is_member(FIRST, date(2016, 1, 1))
    assert not history.is_member(FIRST, date(2019, 1, 1))
    assert history.members_as_of(date(2018, 1, 1)) == (FIRST,)
    assert history.members_as_of(date(2021, 1, 1)) == (SECOND,)


def test_current_constituents_cannot_backfill_past() -> None:
    history = IndexMembershipHistory(
        INDEX,
        [IndexMembership(INDEX, FIRST, date(2024, 1, 1))],
        coverage_start=date(2020, 1, 1),
        coverage_end=date(2025, 1, 1),
    )

    assert not history.is_member(FIRST, date(2023, 12, 31))
    assert history.is_member(FIRST, date(2024, 1, 1))


def test_overlap_and_wrong_index_are_rejected() -> None:
    with pytest.raises(ValueError, match="overlap"):
        IndexMembershipHistory(
            INDEX,
            [
                IndexMembership(INDEX, FIRST, date(2020, 1, 1), date(2021, 1, 1)),
                IndexMembership(INDEX, FIRST, date(2020, 6, 1)),
            ],
            coverage_start=date(2020, 1, 1),
            coverage_end=date(2022, 1, 1),
        )
    with pytest.raises(ValueError, match="identity"):
        IndexMembershipHistory(
            INDEX,
            [IndexMembership(IndexId("other"), FIRST, date(2020, 1, 1))],
            coverage_start=date(2020, 1, 1),
            coverage_end=date(2022, 1, 1),
        )


def test_outside_coverage_is_unknown_not_nonmembership() -> None:
    history = IndexMembershipHistory(
        INDEX,
        [],
        coverage_start=date(2020, 1, 1),
        coverage_end=date(2021, 1, 1),
    )

    with pytest.raises(UnknownIndexHistoryError):
        history.is_member(FIRST, date(2019, 12, 31))
