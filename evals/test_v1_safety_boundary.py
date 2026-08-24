"""Static final boundary scan for hidden network/trading capabilities and secrets."""

from pathlib import Path
import re


ROOT = Path(__file__).parents[1]


def test_runtime_network_is_confined_to_injected_provider_transport() -> None:
    production = tuple((ROOT / "src/stock_quant").rglob("*.py"))
    forbidden = ("urllib.request", "requests.", "httpx.", "urlopen(", "socket.")
    offenders = {
        str(path.relative_to(ROOT)): token
        for path in production
        for token in forbidden
        if token in path.read_text()
    }
    assert offenders == {}
    provider_api = (ROOT / "src/stock_quant/provider/api.py").read_text()
    assert "class ProviderTransport(Protocol)" in provider_api
    assert 'base_url: str = "https://api.tushare.pro"' in provider_api


def test_daily_research_has_no_trading_or_secret_capability() -> None:
    daily_sources = "\n".join(
        path.read_text() for path in (ROOT / "src/stock_quant/daily").rglob("*.py")
    )
    for forbidden in (
        "stock_quant.backtest",
        "approved_rebalance_intent",
        "submit_order",
        "place_order",
        "Broker",
    ):
        assert forbidden not in daily_sources
    tracked_sources = "\n".join(
        path.read_text(errors="ignore")
        for base in (ROOT / "src", ROOT / "scripts")
        for path in base.rglob("*")
        if path.is_file()
    )
    secret_pattern = re.compile(
        r"AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
    )
    assert secret_pattern.search(tracked_sources) is None
