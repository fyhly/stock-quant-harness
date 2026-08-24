from decimal import Decimal
import pytest
from stock_quant.research import MetricInputError, standard_metrics


def test_exact_return_drawdown_vol_turnover_and_cost_formulas() -> None:
    result = standard_metrics(
        (Decimal(100), Decimal(120), Decimal(90)),
        (Decimal(40), Decimal(20)),
        (Decimal(1),),
    )
    assert result.total_return == Decimal("-0.1")
    assert result.maximum_drawdown == Decimal("-0.25")
    average_equity = Decimal(310) / Decimal(3)
    assert result.one_way_turnover == Decimal(60) / (Decimal(2) * average_equity)
    assert result.cost_ratio == Decimal("0.01") and result.periods == 2


def test_empty_constant_negative_and_extreme_precision() -> None:
    constant = standard_metrics((Decimal(10), Decimal(10)), (), ())
    assert (
        constant.total_return
        == constant.maximum_drawdown
        == constant.annualized_volatility
        == 0
    )
    with pytest.raises(MetricInputError, match="empty"):
        standard_metrics((), (), ())
    with pytest.raises(MetricInputError, match="positive"):
        standard_metrics((Decimal(-1),), (), ())
    assert (
        standard_metrics((Decimal("1e-20"), Decimal("2e-20")), (), ()).total_return == 1
    )
