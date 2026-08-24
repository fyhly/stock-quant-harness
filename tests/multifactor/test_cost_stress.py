from decimal import Decimal

from stock_quant.multifactor.cost_stress import (
    CostLevel,
    cost_stress,
    render_cost_stress_report,
)


LEVELS = (
    CostLevel("high", Decimal(".002"), Decimal(".001"), Decimal(".003")),
    CostLevel("low", Decimal(".001"), Decimal(".0005"), Decimal(".0015")),
    CostLevel("mid", Decimal(".0015"), Decimal(".0008"), Decimal(".002")),
)


def test_exact_costs_all_levels_monotonic_and_reconcile() -> None:
    result = cost_stress(Decimal(".10"), Decimal(".4"), LEVELS)
    assert tuple(item.level.level_id for item in result.records) == (
        "low",
        "mid",
        "high",
    )
    assert tuple(item.total_cost for item in result.records) == (
        Decimal(".00120"),
        Decimal(".00172"),
        Decimal(".0024"),
    )
    nets = tuple(item.net_return for item in result.records)
    assert nets == (Decimal(".09880"), Decimal(".09828"), Decimal(".0976"))
    assert result.total_levels == result.successful_levels + result.failed_levels == 3


def test_failure_level_turnover_gross_and_escaped_report_remain_visible() -> None:
    result = cost_stress(
        Decimal("-.02"),
        Decimal("1.25"),
        LEVELS,
        failures={"mid": "simulation <failed>"},
    )
    assert len(result.records) == 3 and result.failed_levels == 1
    failed = next(item for item in result.records if not item.succeeded)
    assert failed.turnover == Decimal("1.25") and failed.gross_return == Decimal("-.02")
    assert failed.net_return is None and failed.failure_message == "simulation <failed>"
    report = render_cost_stress_report(result)
    assert "RESEARCH ONLY" in report and "simulation &lt;failed&gt;" in report
    assert "Total: 3; succeeded: 2; failed: 1" in report
    assert "http://" not in report and "https://" not in report
