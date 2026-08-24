# Phase 11 ExecPlan — Benchmark Factor / Strategy Library

Status: COMPLETED

## Objective

建立预定义、可解释、无参数挖掘的 Momentum/Reversal/Low-Vol/Value/Quality/Technical benchmark configs and runs，用于校准平台而非寻找“圣杯”。

## Ordered task contracts

All tasks use existing PIT Feature→Strategy→Portfolio→Risk→Backtest APIs and frozen/offline fixtures. Allowed: `stock_quant.benchmark`, benchmark configs/tests/reports. Forbidden: Provider/network, core semantic changes, adaptive parameter search, OOS claims, cherry-picking or Phase 12 registry work.

### P11-M11.1-T1 — Momentum benchmark
- Output: fixed 20/60/120 momentum baseline config/result contract and cross-window sanity runs.
- Tests: cutoff, config identity, deterministic ranking/run; no parameter selection.
- Risk: HIGH; Commit: `feat(benchmark): add momentum benchmark`

### P11-M11.2-T1 — Reversal benchmark
- Output: fixed 5/10 reversal baseline with explicit sign/timing.
- Tests: sequence/cutoff/cross-sample determinism.
- Risk: HIGH; Commit: `feat(benchmark): add reversal benchmark`

### P11-M11.3-T1 — Low-vol benchmark
- Output: fixed realized/downside low-vol ranking config.
- Tests: formula direction, missing/min-observation policy and repeatability.
- Risk: HIGH; Commit: `feat(benchmark): add low vol benchmark`

### P11-M11.4-T1 — Value benchmark
- Output: fixed value baseline using announcement-available observations only.
- Tests: PIT announcement/revision, invalid denominators and deterministic run.
- Risk: HIGH; Commit: `feat(benchmark): add value benchmark`

### P11-M11.5-T1 — Quality benchmark
- Output: fixed quality baseline using PIT statements.
- Tests: announcement/restatement leakage and deterministic ranking.
- Risk: HIGH; Commit: `feat(benchmark): add quality benchmark`

### P11-M11.6-T1 — Technical benchmarks
- Output: fixed moving-average and prior-window breakout sanity signals with next-session eligibility and research-only report.
- Tests: rolling boundary, same-bar/future rejection, deterministic signals and failure cases retained.
- Risk: HIGH; Commit: `feat(benchmark): add technical benchmarks`

## Verification and Gate

Focused Ruff/Mypy/tests and leakage/timing/determinism regressions. Gate requires every fixed benchmark run/explanation, no tuning/OOS claim/leakage, all Reviews PASS and one `make verify` closure.

## Evidence

- M11.1–M11.6 — PASS in commits `15ec4cd`, `023e173`, `2f4c594`,
  `db76bd6`, `013dad2`, `2278f3a`; six focused tests plus Ruff/Mypy passed.
- Review confirmed fixed configs, PIT financial selection, prior-session-only
  technical signals, deterministic ties and next-session eligibility. The
  report exposes missing/failure cases and makes no parameter, winner or OOS
  claim.
- Main-Agent Phase Gate `make verify` PASS on 2026-08-24: Ruff PASS, Mypy PASS
  (81 sources), tests PASS (251), evals PASS (1).

## Review decision

- Milestone Reviews M11.1–M11.6: PASS
- Phase 11 Review: PASS
- Residual: calibration scores/signals are not profitability evidence; technical
  callers must explicitly choose a research price view.
