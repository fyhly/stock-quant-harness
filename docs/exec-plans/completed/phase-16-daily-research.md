# Phase 16 ExecPlan — Daily Selection / Rebalance Research

Status: COMPLETED

## Objective

建立可重放、幂等、失败关闭的每日离线研究流水线，从显式数据更新到 PIT Universe、Factor、候选、风险目标与人工报告，全程无真实订单副作用。

## Ordered task contracts

Allowed: `stock_quant.daily`, daily configs/tests/reports/scripts and existing adapters. Network only through explicit Phase 9 acquisition boundary. Forbidden: broker/account/browser automation/order objects or submission, quality bypass, overwrite old good data, current-state fallback, untraceable signals or post-Phase16 platform expansion.

### P16-M16.1-T1 — Daily data update
- Output: idempotent staged daily update orchestration over Provider sync with run/data identities, watermark and recovery state.
- Tests: repeat, partial/network/schema failure, atomic publish/no old overwrite and no implicit network.
- Risk: HIGH; Commit: `feat(daily): add daily data update`

### P16-M16.2-T1 — Daily quality gate
- Output: configured fail-closed gate over freshness/coverage/hash/schema/duplicates/OHLC/calendar status with typed failures.
- Tests: missing/stale/corrupt/anomalous samples, warnings vs fatal, no downstream invocation on fail.
- Risk: HIGH; Commit: `feat(daily): add quality gate`

### P16-M16.3-T1 — Universe refresh
- Output: daily PIT UniverseSnapshot using only validated local artifacts and traceable rule/data versions.
- Tests: historical replay/current-state leakage/missing facts and deterministic exclusions.
- Risk: HIGH; Commit: `feat(daily): refresh universe`

### P16-M16.4-T1 — Factor refresh
- Output: daily factor snapshot with decision cutoff, PIT financial availability, lineage/config identity and failure records.
- Tests: decision-day/future/announcement leakage, incomplete universe, deterministic output.
- Risk: HIGH; Commit: `feat(daily): refresh factors`

### P16-M16.5-T1 — Candidate selection
- Output: ranked candidates with scores, filters, inclusion/exclusion reasons and complete failure visibility.
- Tests: ranking/ties/filtering/reasons/input order and no silent drop.
- Risk: HIGH; Commit: `feat(daily): generate candidates`

### P16-M16.6-T1 — Portfolio/Risk research view
- Output: target portfolio and RiskDecision/summary only; explicit non-order research intent and turnover/cost reference.
- Tests: constraints/infeasible fail, mandatory RiskEngine, no execution/order type/import/side effect.
- Risk: CRITICAL boundary; Commit: `feat(daily): generate portfolio risk view`

### P16-M16.7-T1 — Daily report
- Output: deterministic self-contained Markdown/HTML with run/Git/data/config/universe/factor/risk identities, candidates/reasons/failures/limitations and research-only/manual-decision labels.
- Tests: offline render/escaping/required identities, quality-fail report is not normal signal.
- Risk: HIGH; Commit: `feat(daily): generate research report`

### P16-M16.8-T1 — Historical replay
- Output: command/service reconstructing any covered daily report from pinned local inputs and verifying exact fingerprint without acquisition/network.
- Tests: exact repeat, tamper/missing/drift/date-coverage failure, no network/order side effect.
- Risk: HIGH; Commit: `feat(daily): add historical replay`

## Verification and Gate

Focused Ruff/Mypy/tests plus failure-recovery, PIT/leakage, no-downstream-on-quality-fail, deterministic replay and forbidden-order/import scans. Gate requires repeatable Daily Pipeline, fail-closed quality, no real-trading side effect, all Reviews PASS and one `make verify` closure, then V1 Final Audit preparation only.

## Evidence

- M16.1–M16.8 — PASS in commits `048deb7`, `bca68fe`, `39de133`,
  `439a581`, `3bb9655`, `e47319f`, `91345c3`, `539b1f5`; 16 focused daily
  tests plus Ruff/Mypy passed.
- Review confirmed staged idempotent update, fatal-quality zero downstream calls,
  PIT Universe/factors, complete candidate reasons, RiskDecision-only portfolio
  view, manual-decision reports and local-input fingerprinted replay.
- Forbidden scan found no production Daily import/reference to backtest execution,
  broker, orders, fills or approved rebalance intent.
- Main-Agent Phase Gate `make verify` PASS on 2026-08-24: Ruff PASS, Mypy PASS
  (121 sources), tests PASS (325), evals PASS (1).

## Review decision

- Milestone Reviews M16.1–M16.8: PASS
- Phase 16 Review: PASS
- No Phase 17 expansion or real-trading side effect. Proceed only to V1 Final Audit.
- Residual: daily failed aggregate state is not separately persisted; per-factor
  failures remain explicit; replay callback capability isolation also requires
  runtime audit of injected implementations.
