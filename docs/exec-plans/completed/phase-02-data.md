# Phase 2 ExecPlan — Historical market-data layer

Status: COMPLETED

## Objective

建立完全离线、不可变且可追溯的 Raw→Normalized→Quality→Lineage 数据闭环；本阶段不接外部 Provider。

## Ordered task contracts

### P02-M2.1-T1 — Immutable Raw Artifacts

- Phase/Milestone: Phase 2 / M2.1
- Goal: implement a local `RawArtifactStore` with canonical metadata (`source`, query, fetch time, content hash, schema/version) and append-only writes.
- Dependencies: Phase 1 PASS
- Allowed: `stock_quant.data` raw models/store, tests, docs/exports
- Forbidden: HTTP/provider code, overwrite/delete API, secrets, normalized parsing
- Input: explicit bytes plus typed metadata
- Output: content-addressed immutable artifacts and verifiable manifest
- Tests: stable hash, append-only/idempotent same-content behavior, collision/tamper/path traversal/invalid metadata rejection
- Acceptance: old Raw cannot be overwritten and provider/source provenance is retained
- Risk: HIGH (provenance/integrity)
- Commit: `feat(data): add immutable raw artifacts`

### P02-M2.2-T1 — Versioned DailyBar schema

- Phase/Milestone: Phase 2 / M2.2
- Goal: define validated unadjusted daily OHLCV records and deterministic series ordering using `SecurityId`.
- Dependencies: M2.1 PASS
- Allowed: bar schema/validation, tests, exports
- Forbidden: adjusted-price/execution semantics, network/storage, future filling
- Input: explicit local fields and schema version
- Output: immutable `DailyBar` and series validation
- Tests: OHLC invariants, nonnegative volume/amount, duplicate/out-of-order dates, type/time-zone boundaries
- Acceptance: schema is versioned, identifiers unified, invalid data fails explicitly
- Risk: HIGH (market-data semantics)
- Commit: `feat(data): define normalized daily bars`

### P02-M2.3-T1 — Deterministic local storage

- Phase/Milestone: Phase 2 / M2.3
- Goal: add an offline reader/writer and fixed partition convention for normalized bars, with deterministic round-trip/order and atomic no-overwrite publication.
- Dependencies: M2.2 PASS
- Allowed: local storage adapter, dependency update if essential and pinned, tests, exports
- Forbidden: network/object storage, overwrite, adjusted values, silently lossy serialization
- Input: validated DailyBars and artifact identity
- Output: partitioned local columnar artifact (Parquet when supported) plus manifest
- Tests: round-trip, deterministic bytes/order where format permits, partition/path validation, collision/tamper/atomic failure
- Acceptance: offline read works and directory/schema convention is fixed
- Risk: HIGH (persistence/integrity)
- Commit: `feat(data): add parquet storage`

### P02-M2.4-T1 — Data quality

- Phase/Milestone: Phase 2 / M2.4
- Goal: detect duplicates, ordering/gaps and OHLC/volume anomalies with explicit severity and a deterministic quality report.
- Dependencies: M2.3 PASS
- Allowed: quality rules/report, focused tests, exports
- Forbidden: silently repairing/dropping bad rows, assuming weekday calendar, provider access
- Input: bars plus optional injected TradingCalendar
- Output: issues/report with severity and evidence
- Tests: duplicates, price invariants, missing expected trading dates, empty/clean/extreme cases
- Acceptance: anomalies are never silent and severity is explicit
- Risk: HIGH (data trust)
- Commit: `feat(data): add quality checks`

### P02-M2.5-T1 — Lineage

- Phase/Milestone: Phase 2 / M2.5
- Goal: link every normalized artifact to immutable Raw inputs, transform/schema identity, content hash, code/config identity and quality result.
- Dependencies: M2.4 PASS
- Allowed: lineage model/store, integration tests, exports/docs
- Forbidden: lineage without Raw identity, mutable links, fabricated provenance
- Input: persisted Raw/Normalized identities and quality report
- Output: immutable deterministic lineage record and verification
- Tests: full trace, missing/tampered parent rejection, deterministic identity, multi-parent ordering
- Acceptance: any normalized artifact is traceable to Raw
- Risk: HIGH (auditability)
- Commit: `feat(data): add lineage metadata`

## Verification

Each milestone runs focused unit/integration, Ruff and Mypy checks. Integrity, temporal, no-overwrite, deterministic and tamper regressions are mandatory. Phase Gate runs one `make verify` closure.

## Boundaries

No network, real Provider, broker/account/order behavior, or automatic repair. External bytes are caller-supplied; research reads only validated local artifacts. Raw history is append-only and failures leave prior artifacts intact.

## Phase gate

- M2.1–M2.5 Reviews PASS and ordered commits exist.
- Raw→Normalized→Quality→Lineage integration is demonstrated.
- Reads require no network and every normalized artifact traces to Raw.
- One non-duplicative `make verify` passes; evidence is archived.

## Evidence

- M2.1 — PASS: `a2444eb`; 10 focused Raw tests plus Ruff/Mypy cover canonical
  identity, deep metadata immutability, append-only/idempotent publication,
  traversal/collision/tamper rejection and provenance retention.
- M2.2 — PASS: `d19977b`; 11 focused bar tests plus Ruff/Mypy cover versioned
  unadjusted OHLCV invariants, exact numeric types, identifiers, duplicates and
  ordering.
- M2.3 — PASS: `5ab4b7b`; 7 focused storage tests plus Ruff/Mypy use genuine
  Parquet (`PAR1`) through pinned PyArrow, fixed schema/partition/metadata,
  deterministic round-trip, atomic no-overwrite publication and tamper checks.
- M2.4 — PASS: `1e01c3e`; 6 focused quality tests plus Ruff/Mypy cover clean,
  empty, corrupt, duplicate/order, injected-calendar gap and severity behavior;
  reporting does not mutate input.
- M2.5 — PASS: `c66ed4a`; 6 focused lineage tests and 16 combined Raw/Lineage
  regressions plus Ruff/Mypy cover complete trace, actual parent verification,
  missing/fabricated/tampered parents, deterministic multi-parent identity and
  quality linkage.
- Main-Agent review found no network imports or overwrite path in runtime data
  modules. Intentional filesystem mutation appears only in atomic temporary
  cleanup; direct payload rewrites are confined to tamper tests.
- Main-Agent Phase Gate: `make verify` PASS on 2026-08-24; Ruff PASS, Mypy PASS
  (12 sources), tests PASS (72), evals PASS (1). This was the single complete,
  non-duplicative closure.

## Review decision

- Milestone Reviews M2.1–M2.5: PASS
- Phase 2 Review: PASS
- Scope/boundary: no Provider, network data fetch, brokerage, repair-in-place,
  or Phase 3 implementation. The startup pack remains untracked.
- Residual risk: physical Parquet byte identity is guaranteed for the pinned
  PyArrow/platform used by this project; lineage also retains a logical hash.
  Normalized partitions intentionally constrain one security/year and fixed
  numeric scales, failing explicitly outside those bounds.
