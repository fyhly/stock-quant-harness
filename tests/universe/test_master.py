import pytest

from stock_quant.domain import Exchange, MarketSegment, SecurityId
from stock_quant.universe import (
    ConflictingSecurityMetadataError,
    DuplicateSecurityError,
    SecurityMaster,
    SecurityMetadata,
    UnknownSecurityError,
)


SH = SecurityId("600000", Exchange.SHANGHAI)
SZ = SecurityId("000001", Exchange.SHENZHEN)


def test_lookup_and_deterministic_order_are_as_of_neutral() -> None:
    sh = SecurityMetadata(SH, "Pudong Development Bank")
    sz = SecurityMetadata(SZ, "Ping An Bank")
    master = SecurityMaster([sh, sz])

    assert master.securities == tuple(sorted((sh, sz)))
    assert master.get(SH) is sh
    assert sh.market_segment is MarketSegment.MAIN_BOARD


def test_duplicate_and_conflict_are_distinct_errors() -> None:
    item = SecurityMetadata(SH, "Historical Name")
    with pytest.raises(DuplicateSecurityError):
        SecurityMaster([item, item])
    with pytest.raises(ConflictingSecurityMetadataError):
        SecurityMaster([item, SecurityMetadata(SH, "Conflicting Name")])


def test_delisted_or_failed_identity_is_not_removed() -> None:
    # The master intentionally has no current/listed flag that could drop this row.
    historical_failure = SecurityMetadata(SH, "Retained Delisted Security")

    assert SecurityMaster([historical_failure]).securities == (historical_failure,)


def test_unknown_identity_fails_explicitly() -> None:
    with pytest.raises(UnknownSecurityError):
        SecurityMaster([]).get(SH)


def test_invalid_metadata_is_rejected() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        SecurityMetadata(SH, "")
    with pytest.raises(ValueError, match="whitespace"):
        SecurityMetadata(SH, " padded ")
