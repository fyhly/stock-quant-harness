import pytest

from stock_quant.domain import Exchange, MarketSegment, SecurityId


@pytest.mark.parametrize(
    ("identifier", "segment"),
    [
        (SecurityId("600000", Exchange.SHANGHAI), MarketSegment.MAIN_BOARD),
        (SecurityId("688001", Exchange.SHANGHAI), MarketSegment.STAR_MARKET),
        (SecurityId("000001", Exchange.SHENZHEN), MarketSegment.MAIN_BOARD),
        (SecurityId("300001", Exchange.SHENZHEN), MarketSegment.CHINEXT),
    ],
)
def test_explicit_exchange_mapping(
    identifier: SecurityId, segment: MarketSegment
) -> None:
    assert identifier.market_segment is segment


@pytest.mark.parametrize("code", ["60000", "6000000", "６０００００", "ABC123"])
def test_invalid_code_format_is_rejected(code: str) -> None:
    with pytest.raises(ValueError):
        SecurityId(code, Exchange.SHANGHAI)


def test_wrong_or_unknown_exchange_mapping_is_rejected() -> None:
    with pytest.raises(ValueError):
        SecurityId("600000", Exchange.SHENZHEN)
    with pytest.raises(ValueError):
        SecurityId("900901", Exchange.SHANGHAI)
    with pytest.raises(ValueError, match="unsupported exchange"):
        SecurityId.parse("600000.SH")


def test_canonical_round_trip_equality_and_hash() -> None:
    identifier = SecurityId("601398", Exchange.SHANGHAI)

    assert SecurityId.parse(str(identifier)) == identifier
    assert len({identifier, SecurityId.parse("601398.XSHG")}) == 1


def test_parse_requires_explicit_exchange() -> None:
    with pytest.raises(ValueError, match="CODE.MIC"):
        SecurityId.parse("600000")
