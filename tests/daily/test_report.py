from stock_quant.daily.quality import DailyQualityEvidence
from stock_quant.daily.report import REQUIRED_IDENTITIES, render_daily_report


IDENTITIES = {
    name: chr(97 + index) * 64 for index, name in enumerate(REQUIRED_IDENTITIES)
}


def test_quality_fail_report_is_not_a_normal_signal_and_is_offline_escaped() -> None:
    report = render_daily_report(
        identities=IDENTITIES,
        quality=DailyQualityEvidence(False, ("bad <hash>",), (), ()),
        candidates=None,
        risk_view=None,
        failures=("failure <visible>",),
        limitations=("manual review",),
    )
    assert report == render_daily_report(
        identities=IDENTITIES,
        quality=DailyQualityEvidence(False, ("bad <hash>",), (), ()),
        candidates=None,
        risk_view=None,
        failures=("failure <visible>",),
        limitations=("manual review",),
    )
    assert report.status == "QUALITY_FAILED_NO_SIGNAL"
    assert "&lt;hash&gt;" in report.html and "&lt;visible&gt;" in report.html
    assert "RESEARCH ONLY — MANUAL DECISION REQUIRED" in report.html
    assert "http://" not in report.html and "https://" not in report.html


def test_all_required_identities_are_rendered_and_missing_rejected() -> None:
    report = render_daily_report(
        identities=IDENTITIES,
        quality=DailyQualityEvidence(False, ("fatal",), (), ()),
        candidates=None,
        risk_view=None,
        failures=(),
        limitations=(),
    )
    assert all(value in report.html for value in IDENTITIES.values())
    broken = dict(IDENTITIES)
    broken.pop("risk")
    try:
        render_daily_report(
            identities=broken,
            quality=DailyQualityEvidence(False, ("fatal",), (), ()),
            candidates=None,
            risk_view=None,
            failures=(),
            limitations=(),
        )
    except ValueError:
        pass
    else:
        raise AssertionError("missing identity accepted")
