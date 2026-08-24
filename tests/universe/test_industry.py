from datetime import date

import pytest

from stock_quant.domain import Exchange, SecurityId
from stock_quant.universe import (
    IndustryMembership,
    IndustryMembershipHistory,
    IndustryTaxonomy,
    UnknownIndustryHistoryError,
)


SECURITY = SecurityId("600000", Exchange.SHANGHAI)
TAXONOMY = IndustryTaxonomy("CITICS", "2024-v1")


def test_classification_changes_and_boundaries_are_point_in_time() -> None:
    history = IndustryMembershipHistory(
        TAXONOMY,
        [
            IndustryMembership(
                TAXONOMY, SECURITY, "BANK", date(2010, 1, 1), date(2020, 1, 1)
            ),
            IndustryMembership(TAXONOMY, SECURITY, "FINANCE", date(2020, 1, 1)),
        ],
    )

    assert history.classification_as_of(SECURITY, date(2019, 12, 31)).industry_code == (
        "BANK"
    )
    assert history.classification_as_of(SECURITY, date(2020, 1, 1)).industry_code == (
        "FINANCE"
    )
    # Current FINANCE cannot overwrite the older BANK classification.
    assert history.classification_as_of(SECURITY, date(2015, 1, 1)).industry_code == (
        "BANK"
    )


def test_gap_and_missing_security_are_unknown() -> None:
    history = IndustryMembershipHistory(
        TAXONOMY,
        [
            IndustryMembership(
                TAXONOMY, SECURITY, "BANK", date(2010, 1, 1), date(2015, 1, 1)
            ),
            IndustryMembership(TAXONOMY, SECURITY, "FINANCE", date(2016, 1, 1)),
        ],
    )

    with pytest.raises(UnknownIndustryHistoryError):
        history.classification_as_of(SECURITY, date(2015, 6, 1))
    with pytest.raises(UnknownIndustryHistoryError):
        history.classification_as_of(
            SecurityId("000001", Exchange.SHENZHEN), date(2020, 1, 1)
        )


def test_overlap_and_taxonomy_mismatch_are_rejected() -> None:
    with pytest.raises(ValueError, match="overlap"):
        IndustryMembershipHistory(
            TAXONOMY,
            [
                IndustryMembership(
                    TAXONOMY, SECURITY, "BANK", date(2010, 1, 1), date(2020, 1, 1)
                ),
                IndustryMembership(TAXONOMY, SECURITY, "FINANCE", date(2019, 1, 1)),
            ],
        )
    with pytest.raises(ValueError, match="taxonomy"):
        IndustryMembershipHistory(
            TAXONOMY,
            [
                IndustryMembership(
                    IndustryTaxonomy("SW", "v1"),
                    SECURITY,
                    "BANK",
                    date(2010, 1, 1),
                )
            ],
        )


def test_taxonomy_version_is_part_of_identity() -> None:
    assert IndustryTaxonomy("CITICS", "2024-v1") != IndustryTaxonomy(
        "CITICS", "2025-v1"
    )
