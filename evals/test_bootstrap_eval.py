import stock_quant


def test_public_surface_is_offline_bootstrap_only() -> None:
    # Imported submodules are automatically attached to their parent package by
    # Python and therefore cannot be used to infer the declared root API.  The
    # explicit export contract remains stable regardless of collection order.
    assert stock_quant.__all__ == ["__version__"]
    assert stock_quant.__version__ == "0.1.0"
