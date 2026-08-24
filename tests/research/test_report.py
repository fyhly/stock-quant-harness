import hashlib

from stock_quant.research.artifacts import RunArtifacts
from stock_quant.research.manifest import IDENTITY_FIELDS, create_manifest
from stock_quant.research.report import render_html_report
from stock_quant.research.run_id import RunId


def test_report_is_deterministic_complete_self_contained_and_escaped() -> None:
    run_id = RunId("20240102T030405000000Z-0123456789abcdef0123456789abcdef")
    identities = {
        name: hashlib.sha256(name.encode()).hexdigest() for name in IDENTITY_FIELDS
    }
    manifest = create_manifest(run_id, identities)
    artifacts = RunArtifacts(run_id, (("equity.parquet", "a" * 64),))
    args = (
        manifest,
        artifacts,
        {"return<script>": "1&2"},
        ("bad <script>alert(1)</script>",),
        ("research—not investment advice",),
    )
    first = render_html_report(*args)
    assert first == render_html_report(*args)
    assert "RESEARCH ONLY" in first
    for heading in ("Identities", "Artifacts", "Metrics", "Failures", "Limitations"):
        assert f"<h2>{heading}</h2>" in first
    assert "&lt;script&gt;" in first and "1&amp;2" in first
    assert "<script>" not in first
    assert "http://" not in first and "https://" not in first
    assert "<link" not in first and "src=" not in first
