from datetime import date, datetime

import pytest

from stock_quant.domain import (
    StatusInterval,
    STStatus,
    STStatusHistory,
    TradeStatus,
    TradeStatusHistory,
    UnknownStatusError,
)


def test_st_transitions_use_half_open_boundaries() -> None:
    history = STStatusHistory(
        [
            StatusInterval(STStatus.NORMAL, date(2020, 1, 1), date(2021, 5, 6)),
            StatusInterval(STStatus.ST, date(2021, 5, 6), date(2022, 4, 1)),
            StatusInterval(STStatus.NORMAL, date(2022, 4, 1)),
        ]
    )

    assert history.as_of(date(2021, 5, 5)) is STStatus.NORMAL
    assert history.as_of(date(2021, 5, 6)) is STStatus.ST
    assert history.as_of(date(2022, 4, 1)) is STStatus.NORMAL


def test_suspension_transition_is_historical_not_execution_logic() -> None:
    history = TradeStatusHistory(
        [
            StatusInterval(
                TradeStatus.TRADING, date(2024, 1, 1), date(2024, 1, 8)
            ),
            StatusInterval(
                TradeStatus.SUSPENDED, date(2024, 1, 8), date(2024, 1, 10)
            ),
            StatusInterval(TradeStatus.TRADING, date(2024, 1, 10)),
        ]
    )

    assert history.as_of(date(2024, 1, 8)) is TradeStatus.SUSPENDED
    assert history.as_of(date(2024, 1, 10)) is TradeStatus.TRADING


def test_temporal_gap_fails_closed() -> None:
    history = STStatusHistory(
        [
            StatusInterval(STStatus.NORMAL, date(2020, 1, 1), date(2020, 2, 1)),
            StatusInterval(STStatus.ST, date(2020, 3, 1)),
        ]
    )

    with pytest.raises(UnknownStatusError):
        history.as_of(date(2020, 2, 15))
    with pytest.raises(UnknownStatusError):
        history.as_of(date(2019, 12, 31))


def test_overlap_and_nonfinal_open_interval_are_rejected() -> None:
    with pytest.raises(ValueError, match="overlap"):
        STStatusHistory(
            [
                StatusInterval(
                    STStatus.NORMAL, date(2020, 1, 1), date(2020, 3, 1)
                ),
                StatusInterval(STStatus.ST, date(2020, 2, 1)),
            ]
        )
    with pytest.raises(ValueError, match="final"):
        TradeStatusHistory(
            [
                StatusInterval(TradeStatus.TRADING, date(2020, 1, 1)),
                StatusInterval(TradeStatus.SUSPENDED, date(2020, 2, 1)),
            ]
        )


def test_current_status_cannot_contaminate_past_lookup() -> None:
    history = STStatusHistory(
        [
            StatusInterval(STStatus.NORMAL, date(2010, 1, 1), date(2024, 5, 1)),
            StatusInterval(STStatus.STAR_ST, date(2024, 5, 1)),
        ]
    )

    assert history.as_of(date(2020, 1, 1)) is STStatus.NORMAL
    assert history.as_of(date(2025, 1, 1)) is STStatus.STAR_ST


def test_history_is_sorted_and_exposed_as_immutable_tuple() -> None:
    later = StatusInterval(STStatus.ST, date(2021, 1, 1))
    earlier = StatusInterval(STStatus.NORMAL, date(2020, 1, 1), date(2021, 1, 1))
    history = STStatusHistory([later, earlier])

    assert history.intervals == (earlier, later)


def test_datetime_is_rejected_and_status_types_cannot_mix() -> None:
    with pytest.raises(TypeError):
        StatusInterval(STStatus.NORMAL, datetime(2020, 1, 1))
    with pytest.raises(TypeError, match="STStatus"):
        STStatusHistory(
            [StatusInterval(TradeStatus.TRADING, date(2020, 1, 1))]  # type: ignore[arg-type]
        )
