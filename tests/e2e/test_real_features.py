from datetime import date
from pathlib import Path
from stock_quant.domain import TradingDay
from stock_quant.e2e import compute_real_features

ROOT = Path(__file__).parents[1] / "fixtures" / "real" / "v1"
DAY = TradingDay(date(2024, 12, 16))


def test_real_momentum_volatility_are_deterministic_and_lineaged() -> None:
    first = compute_real_features(ROOT, DAY)
    assert first == compute_real_features(ROOT, DAY) and len(first.rows) == 2
    assert len(first.lineage) == 64 and all(
        row.realized_volatility_20 >= 0 for row in first.rows
    )


def test_feature_cutoff_excludes_decision_close() -> None:
    result = compute_real_features(ROOT, DAY)
    assert result.decision_cutoff.hour == 15 and result.decision_day == DAY
