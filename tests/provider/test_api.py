from stock_quant.provider import FakeTransport, ProviderQuery, redact


def test_canonical_query_fake_transport_and_identity() -> None:
    query = ProviderQuery(
        "daily", ("close", "ts_code"), (("trade_date", "20240101"),), "tushare-daily-v1"
    )
    fake = FakeTransport({"daily": b"response"})
    assert fake.request(query, credential="secret").exact_bytes == b"response"
    assert (
        query.identity
        == ProviderQuery(
            "daily",
            ("close", "ts_code"),
            (("trade_date", "20240101"),),
            "tushare-daily-v1",
        ).identity
    )


def test_secret_is_completely_redacted_and_backtest_has_no_provider_import() -> None:
    secret = "token-123"
    assert secret not in redact({"token": secret}, (secret,))
    import stock_quant.backtest as backtest

    assert all("provider" not in str(value) for value in vars(backtest).values())
