from datetime import date

from stock_quant.domain import (
    Exchange,
    SecurityId,
    StatusInterval,
    STStatus,
    STStatusHistory,
)
from stock_quant.universe import (
    ExclusionCode,
    HistoricalSTFilter,
    STEligibilityPolicy,
)


SECURITY = SecurityId("600000", Exchange.SHANGHAI)


def history() -> STStatusHistory:
    return STStatusHistory(
        [
            StatusInterval(STStatus.NORMAL, date(2010, 1, 1), date(2020, 5, 1)),
            StatusInterval(STStatus.ST, date(2020, 5, 1), date(2021, 6, 1)),
            StatusInterval(STStatus.STAR_ST, date(2021, 6, 1)),
        ]
    )


def test_historical_transition_and_present_status_do_not_contaminate_past() -> None:
    rule = HistoricalSTFilter(
        {SECURITY: history()}, STEligibilityPolicy("exclude-st-v1")
    )

    assert rule.evaluate(SECURITY, date(2019, 1, 1)).eligible
    st = rule.evaluate(SECURITY, date(2020, 5, 1))
    star_st = rule.evaluate(SECURITY, date(2021, 6, 1))
    assert st.exclusion is not None and st.exclusion.code is ExclusionCode.ST_STATUS
    assert star_st.exclusion is not None
    assert star_st.exclusion.evidence[-1] == ("status", "STAR_ST")
    assert rule.evaluate(SECURITY, date(2015, 1, 1)).eligible


def test_explicit_policy_can_distinguish_st_categories() -> None:
    rule = HistoricalSTFilter(
        {SECURITY: history()},
        STEligibilityPolicy("allow-st-only-v1", allow_st=True, allow_star_st=False),
    )

    assert rule.evaluate(SECURITY, date(2020, 5, 1)).eligible
    assert not rule.evaluate(SECURITY, date(2021, 6, 1)).eligible


def test_missing_or_gapped_history_fails_closed() -> None:
    missing = HistoricalSTFilter({}, STEligibilityPolicy("v1"))
    gapped = HistoricalSTFilter(
        {
            SECURITY: STStatusHistory(
                [
                    StatusInterval(
                        STStatus.NORMAL, date(2020, 1, 1), date(2020, 2, 1)
                    ),
                    StatusInterval(STStatus.ST, date(2020, 3, 1)),
                ]
            )
        },
        STEligibilityPolicy("v1"),
    )

    for rule in (missing, gapped):
        decision = rule.evaluate(SECURITY, date(2020, 2, 15))
        assert decision.exclusion is not None
        assert decision.exclusion.code is ExclusionCode.MISSING_ST_HISTORY
