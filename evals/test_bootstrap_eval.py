import stock_quant


def test_public_surface_is_offline_bootstrap_only() -> None:
    public_names = {name for name in vars(stock_quant) if not name.startswith("_")}

    assert public_names == set()
    assert stock_quant.__all__ == ["__version__"]
