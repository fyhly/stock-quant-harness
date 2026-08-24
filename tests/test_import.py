def test_package_import() -> None:
    import stock_quant

    assert stock_quant.__version__ == "0.1.0"
