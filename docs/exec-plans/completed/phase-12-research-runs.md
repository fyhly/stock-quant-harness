# Phase 12 ExecPlan — Standardized Experiments and Reports

Status: COMPLETED

## Objective

让每个正式研究运行都有唯一 ID、不可变 manifest/artifacts、统一指标与离线报告，并可按 run_id 精确重放。

## Ordered task contracts

Allowed: `stock_quant.research`, `reports/research`, configs/tests/docs and narrow BacktestResult adapters. Forbidden: Provider/network, mutable overwrite, result cherry-picking, core semantic changes, OOS claims or Phase 13.

### P12-M12.1-T1 — Run ID
- Output: collision-safe canonical RunId and append-only local registry with status/timestamps.
- Tests: uniqueness, canonical validation, concurrent/no-overwrite behavior and lookup.
- Risk: HIGH; Commit: `feat(research): add run ids`

### P12-M12.2-T1 — Manifest
- Output: immutable canonical manifest pinning Git/data/config/universe/features/strategy/portfolio/risk/backtest/schema identities.
- Tests: required fields, hash/determinism, invalid/tampered identity and research-only status.
- Risk: HIGH; Commit: `feat(research): add experiment manifest`

### P12-M12.3-T1 — Artifacts
- Output: atomic run store for trades/holdings/equity/metrics/failures in stable Parquet/JSON schemas.
- Tests: round-trip, no-overwrite, partial failure cleanup, tamper and BacktestResult adapter.
- Risk: HIGH; Commit: `feat(research): persist run artifacts`

### P12-M12.4-T1 — Metrics
- Output: explicitly defined return, drawdown, volatility, turnover and cost metrics with period/convention metadata.
- Tests: formulas, empty/constant/negative/extreme series and Decimal precision.
- Risk: HIGH; Commit: `feat(research): add standard metrics`

### P12-M12.5-T1 — Factor analytics
- Output: per-date IC/RankIC and quantile summaries with explicit alignment/missing/tie rules.
- Tests: cross-sectional formula, date alignment, insufficient sample, no future labels in feature inputs.
- Risk: HIGH; Commit: `feat(research): add factor analytics`

### P12-M12.6-T1 — Offline HTML report
- Output: deterministic self-contained HTML from immutable run artifacts, including identities, metrics, failures, limitations and research-only label.
- Tests: offline smoke render, escaping, required sections and deterministic content.
- Risk: MEDIUM; Commit: `feat(research): add html reports`

### P12-M12.7-T1 — Reproduce by run_id
- Output: command/service that loads pinned manifest/artifacts/config, rejects identity drift, reruns deterministic pipeline callback and verifies fingerprint.
- Tests: exact replay, missing/tampered/version mismatch, failure retained and no network.
- Risk: HIGH; Commit: `feat(research): add run reproduction`

## Verification and Gate

Focused Ruff/Mypy/tests plus immutability, identity, formula, no-leakage, offline and reproducibility regressions. Gate requires every formal run has run_id, same conditions reproduce, all Reviews PASS and one `make verify` closure.

## Evidence

- M12.1–M12.7 — PASS in commits `4fcebfb`, `a9ce517`, `22fd820`,
  `d5cb37a`, `1f88b22`, `eeaaeb9`, `2cfa206`; 15 research tests plus
  Ruff/Mypy passed.
- Review confirmed append-only IDs/store, ten pinned identities, atomic
  Parquet/JSON artifacts, explicit Decimal metrics, strict per-date PIT factor
  analytics, escaped self-contained reports and offline drift-rejecting replay.
- Main-Agent Phase Gate `make verify` PASS on 2026-08-24: Ruff PASS, Mypy PASS
  (89 sources), tests PASS (266), evals PASS (1).

## Review decision

- Milestone Reviews M12.1–M12.7: PASS
- Phase 12 Review: PASS
- Residual: empty quantile buckets are explicitly zero-count/zero-mean;
  injected loaders must themselves be append-only; atomic publication assumes
  the store-root filesystem as enforced by staging location.
