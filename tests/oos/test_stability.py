from decimal import Decimal

import pytest

from stock_quant.oos.stability import StabilityError, StabilityWindow, stability_summary


def test_formulas_parameters_factors_negative_and_failures_are_all_visible() -> None:
    rows = (
        StabilityWindow("a", "p1", Decimal(".1"), (("value", Decimal(1)),)),
        StabilityWindow("b", "p1", Decimal("-.2"), (("value", Decimal(3)),)),
        StabilityWindow("c", "p2", None, (), "OOS", "visible failure"),
    )
    result = stability_summary(rows)
    assert (
        result.total_windows == result.successful_windows + result.failed_windows == 3
    )
    assert result.negative_windows == 1 and result.mean_oos_return == Decimal("-.05")
    assert result.parameter_counts == (("p1", 2),)
    assert result.factor_means == (("value", Decimal(2)),)
    assert result.failures == (("c", "OOS", "visible failure"),)


def test_missing_constant_extreme_and_invalid_inputs() -> None:
    failed = stability_summary((StabilityWindow("a", "", None, (), "TRAIN", "bad"),))
    assert (
        failed.mean_oos_return
        == failed.minimum_oos_return
        == failed.maximum_oos_return
        == 0
    )
    extreme = Decimal("1E+100")
    constant = stability_summary(
        (StabilityWindow("a", "p", extreme, ()), StabilityWindow("b", "p", extreme, ()))
    )
    assert (
        constant.mean_oos_return
        == constant.minimum_oos_return
        == constant.maximum_oos_return
        == extreme
    )
    with pytest.raises(StabilityError, match="nonempty"):
        stability_summary(())
    with pytest.raises(StabilityError, match="failure evidence"):
        stability_summary((StabilityWindow("a", "", None, ()),))
