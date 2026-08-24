"""Deterministic, escaped and entirely offline research HTML reports."""

from html import escape
from typing import Mapping, Sequence

from stock_quant.research.artifacts import RunArtifacts
from stock_quant.research.manifest import ExperimentManifest, IDENTITY_FIELDS


def _rows(values: Sequence[tuple[str, str]]) -> str:
    return "".join(
        f"<tr><th>{escape(name)}</th><td>{escape(value)}</td></tr>"
        for name, value in values
    )


def render_html_report(
    manifest: ExperimentManifest,
    artifacts: RunArtifacts,
    metrics: Mapping[str, str],
    failures: Sequence[str],
    limitations: Sequence[str],
) -> str:
    identities = tuple(
        (name, getattr(manifest, f"{name}_identity")) for name in IDENTITY_FIELDS
    )
    metric_rows = tuple(
        sorted((str(key), str(value)) for key, value in metrics.items())
    )
    artifact_rows = tuple(sorted(artifacts.files))

    def items(values: Sequence[str]) -> str:
        return (
            "".join(f"<li>{escape(value)}</li>" for value in values) or "<li>None</li>"
        )

    return (
        '<!doctype html><html><head><meta charset="utf-8">'
        "<title>Research run report</title><style>"
        "body{font-family:sans-serif;max-width:70rem;margin:2rem auto}"
        "table{border-collapse:collapse}th,td{border:1px solid #888;padding:.3rem}"
        ".warning{font-weight:bold;color:#900}</style></head><body>"
        '<h1>Research run report</h1><p class="warning">RESEARCH ONLY</p>'
        f"<p>Run ID: {escape(manifest.run_id.value)}</p>"
        f"<p>Manifest identity: {escape(manifest.manifest_identity)}</p>"
        f"<h2>Identities</h2><table>{_rows(identities)}</table>"
        f"<h2>Artifacts</h2><table>{_rows(artifact_rows)}</table>"
        f"<h2>Metrics</h2><table>{_rows(metric_rows)}</table>"
        f"<h2>Failures</h2><ul>{items(failures)}</ul>"
        f"<h2>Limitations</h2><ul>{items(limitations)}</ul>"
        "</body></html>"
    )
