# Phase 9 ExecPlan — Real-data Provider

Status: COMPLETED

## Objective

建立隔离外部 API 的真实 A 股 Provider 与 raw-first 增量采集闭环。首个适配器采用 Tushare Pro 的未复权日线及相关历史接口；凭据仅在显式采集命令运行时注入，不写入工件或日志。

## Source decision

Tushare official documentation defines `daily` as unadjusted A-share daily data and exposes security master, calendar, limits and related datasets. Adapter behavior is versioned against explicit response schemas. Tests use recorded/synthetic response bytes and never network; Backtest never imports Provider. Lack of runtime credentials fails closed before a request.

## Ordered task contracts

Allowed: `stock_quant.provider`, `scripts`, provider configs, Raw/normalize integration tests and docs. Network is allowed only behind an explicit acquisition command/transport. Forbidden: credentials in Git/artifacts/logs, direct normalize-before-Raw, network in tests/backtest/research reads, adjusted prices as execution data, broker/live orders or Phase 10.

### P09-M9.1-T1 — Provider abstraction
- Goal/output: typed query/response/transport contracts, schema/version/source identities, retryable-vs-terminal errors and fake transport.
- Tests/acceptance: fake provider, canonical queries, secret redaction, Backtest import graph has no Provider.
- Risk: HIGH; Commit: `feat(provider): define data provider interface`

### P09-M9.2-T1 — Market-data Provider
- Goal/output: Tushare unadjusted `daily` acquisition that persists exact response bytes/metadata to Raw before parsing DailyBars.
- Tests/acceptance: recorded response, raw-before-normalize failure ordering, units/Decimal/code/date conversion, schema drift/error payload/duplicates.
- Risk: HIGH; Commit: `feat(provider): add market data provider`

### P09-M9.3-T1 — Security-master Provider
- Goal/output: ingest listed/delisted identities and lifecycle metadata without dropping inactive securities.
- Tests/acceptance: retained delisted records, code mapping, chronology/schema/version failures.
- Risk: HIGH; Commit: `feat(provider): ingest security master`

### P09-M9.4-T1 — Index/industry history Provider
- Goal/output: effective-dated membership/classification ingestion only when source supplies historical dates; otherwise mark capability unavailable rather than current-backfill.
- Tests/acceptance: entry/exit/effective dates, gaps, current-only response rejection.
- Risk: HIGH; Commit: `feat(provider): ingest index and industry history`

### P09-M9.5-T1 — Corporate-action Provider
- Goal/output: dividend/bonus/rights ingestion with announcement/record/ex/pay/credit dates and source lineage.
- Tests/acceptance: date/event mapping, duplicate identity, missing dates and raw trace.
- Risk: HIGH; Commit: `feat(provider): ingest corporate actions`

### P09-M9.6-T1 — Financial Provider
- Goal/output: statement/fundamental observations retaining report period, announcement date, update/revision time and raw identity.
- Tests/acceptance: announcement required, revisions retained, report-period-only response rejected, PIT selection integration.
- Risk: HIGH; Commit: `feat(provider): ingest financial data`

### P09-M9.7-T1 — Incremental sync
- Goal/output: explicit CLI/service sync plan with watermark, immutable Raw append, staged validation/publication, idempotence and failure recovery.
- Tests/acceptance: repeated sync, partial/network/schema failure leaves old normalized data intact, secret redaction and deterministic manifest.
- Risk: HIGH; Commit: `feat(provider): add incremental sync`

## Verification and Gate

Focused Ruff/Mypy/tests plus raw-first ordering, schema drift, PIT, idempotence, failure/recovery and secret regressions. Gate: all real Provider paths persist Raw first, failure cannot contaminate normalized storage, financial announcement time is mandatory, no runtime network outside acquisition, all reviews PASS and one `make verify` closure.

## Evidence

- M9.1–M9.7 — PASS in commits `22f4134`, `56797a6`, `f20bc3f`,
  `166f66d`, `15f8a75`, `1597afc`, `d2a00f2`; 14 focused tests plus
  Ruff/Mypy passed. Exact responses persist Raw before parsing, financial
  announcement/revisions remain available, and sync is staged/idempotent.
- Review rejected an unverifiable assumed Tushare rights schema. Fix `2241fbc`
  restricts the adapter to documented dividend cash/bonus/transfer fields,
  returns CapabilityUnavailable before any rights request, and forces HTTPS.
- Credentials are runtime-only/redacted; tests use FakeTransport; Backtest has
  no Provider import or network path.
- Main-Agent Phase Gate `make verify` PASS on 2026-08-24: Ruff PASS, Mypy PASS
  (72 sources), tests PASS (233), evals PASS (1).

## Review decision

- Milestone Reviews M9.1–M9.7: PASS after Gate remediation
- Phase 9 Review: PASS
- Provider failure cannot publish normalized state; report-period-only financial
  rows and current-only historical membership are rejected.
- Residual risks: Tushare rights ingestion is explicitly unavailable; financial
  revision availability conservatively uses first fetch time where the source
  lacks row timestamps; external publish callbacks must honor staged atomicity.
