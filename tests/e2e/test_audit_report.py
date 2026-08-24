from datetime import date
from pathlib import Path

from stock_quant.domain import TradingDay
from stock_quant.e2e import run_real_backtest


ROOT = Path(__file__).parents[1] / "fixtures" / "real" / "v1"
REPORT = Path(__file__).parents[2] / "docs" / "reports" / "phase-10-real-e2e.md"


def test_audit_report_is_offline_readable_and_trace_complete() -> None:
    text = REPORT.read_text()
    for field in (
        "Source",
        "raw SHA-256",
        "Parquet SHA-256",
        "Config SHA-256",
        "Git commit",
        "Backtest fingerprint",
        "Quality",
        "limitations",
        "RESEARCH ONLY",
    ):
        assert field in text
    result = run_real_backtest(ROOT, TradingDay(date(2024, 11, 29)))
    assert result.fingerprint in text
    assert (
        result.config_identity in text
        and result.data_identity in text
        and result.code_identity in text
    )


def test_report_contains_both_raw_trace_links_and_research_warning() -> None:
    text = REPORT.read_text()
    assert "2659fa363faa1dd2" in text and "cbb2b85e7d7118e4" in text
    assert "not investment advice" in text.lower()
