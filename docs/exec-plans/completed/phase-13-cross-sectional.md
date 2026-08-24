# Phase 13 ExecPlan — Market-wide / Multi-security Research

Status: COMPLETED

## Objective

建立可扩展、确定、失败可见的横截面批处理、IC/RankIC、分层回测与历史行业/风格归因。

## Ordered task contracts

Allowed: `stock_quant.market_research`, research configs/tests/reports and existing research adapters. Forbidden: Provider/network, current-universe/industry backfill, silent row/run dropping, parameter winner selection, OOS claims or Phase 14.

### P13-M13.1-T1 — Market Universe Gate
- Output: coverage/quality/min-security thresholds and typed pass/fail evidence over PIT snapshots.
- Tests: coverage boundaries, missing/bad samples, retained exclusion reasons and deterministic gate.
- Risk: HIGH; Commit: `feat(research): add market universe gate`

### P13-M13.2-T1 — Cross-sectional runner
- Output: deterministic date/security batch runner with bounded partitions, manifests and per-item success/failure records.
- Tests: batching/order/retry identity, partial failures retained and repeat equality.
- Risk: HIGH; Commit: `feat(research): add cross sectional runner`

### P13-M13.3-T1 — IC / RankIC
- Output: aligned per-date IC series and aggregate summaries using existing analytics.
- Tests: formulas/date-only cross sections, insufficient/missing handling, no future label leakage.
- Risk: HIGH; Commit: `feat(research): add ic analytics`

### P13-M13.4-T1 — Quantile backtests
- Output: per-date factor quantile portfolios and forward-return comparison with explicit ties/empty groups/cost convention.
- Tests: complete grouping, no future ranking, group identities and deterministic aggregation.
- Risk: HIGH; Commit: `feat(research): add quantile backtests`

### P13-M13.5-T1 — Sector/style attribution
- Output: PIT sector and declared style exposure/return attribution with taxonomy/version identities.
- Tests: sector changes/gaps, current-industry leakage, reconciliation and missing classification failure.
- Risk: HIGH; Commit: `feat(research): add exposure analytics`

### P13-M13.6-T1 — Failure registry and report
- Output: append-only typed failure registry linked to run/data/Git/config and a research-only full-market summary that includes failures.
- Tests: no silent filtering, idempotence/no-overwrite, report totals reconcile and failure details escape/render offline.
- Risk: HIGH; Commit: `feat(research): retain failed experiments`

## Verification and Gate

Focused Ruff/Mypy/tests plus PIT, batching, failure-retention, date-alignment and deterministic regressions. Gate requires batch research, all failure samples retained/reconciled, all Reviews PASS and one `make verify` closure.

## Evidence

- M13.1–M13.6 — PASS in commits `d9b8fd8`, `d2794f3`, `afdc646`,
  `5a8c2b4`, `ebe5412`, `33ed7f3`; 12 focused tests plus Ruff/Mypy passed.
- Review confirmed PIT universe quality evidence, deterministic batch totals,
  date-aligned IC, prior-cutoff quantile ranking, historical taxonomy attribution
  and append-only escaped failure reporting with exact reconciliation.
- Main-Agent Phase Gate `make verify` PASS on 2026-08-24: Ruff PASS, Mypy PASS
  (96 sources), tests PASS (278), evals PASS (1).

## Review decision

- Milestone Reviews M13.1–M13.6: PASS
- Phase 13 Review: PASS
- Residual: tied ranks may leave explicit empty quantiles; style attribution is
  declared linear contribution plus residual, not fitted regression.
