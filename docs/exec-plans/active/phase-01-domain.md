# Phase 1 ExecPlan — A-share domain model

Status: ACTIVE

## Objective

建立不依赖 Provider 的不可歧义证券标识、历史交易日历及 Point-in-Time 证券状态模型，为后续离线数据层提供严格类型与时间语义。

## Ordered task contracts

### P01-M1.1-T1 — Security identifiers

- Phase/Milestone: Phase 1 / M1.1
- Goal: implement immutable `SecurityId`, `Exchange`, and `MarketSegment` with explicit Shanghai/Shenzhen code mapping and validation.
- Dependencies: Phase 0 PASS
- Allowed: domain package, exports, focused tests, domain documentation
- Forbidden: Provider/network code, universe filtering, permissive guessing of ambiguous identifiers, later-phase behavior
- Input: explicit A-share symbol/exchange values
- Output: typed provider-independent identifiers
- Tests: valid/invalid codes, exchange mapping, equality/hash/round-trip
- Acceptance: identifiers are unambiguous and provider-independent
- Risk: MEDIUM
- Commit: `feat(domain): add security identifiers`

### P01-M1.2-T1 — Trading calendar

- Phase/Milestone: Phase 1 / M1.2
- Goal: implement `TradingDay`, `TradingSession`, and an injected historical `TradingCalendar` without hidden holiday/network assumptions.
- Dependencies: M1.1 PASS
- Allowed: calendar domain module, fixtures/tests, exports
- Forbidden: live calendar fetches, treating weekdays as authoritative exchange history, backtest engine
- Input: explicit local trading dates/session definition
- Output: historical queries including previous/next trading day
- Tests: weekends, supplied holidays, boundaries, ordered/deterministic queries
- Acceptance: calendar semantics are independent and support historical lookup; unknown/out-of-range queries fail explicitly
- Risk: HIGH (time semantics)
- Commit: `feat(domain): add trading calendar`

### P01-M1.3-T1 — Listing lifecycle

- Phase/Milestone: Phase 1 / M1.3
- Goal: model `ListingStatus`, listing date, optional delisting date, and as-of lifecycle queries while retaining delisted securities.
- Dependencies: M1.2 PASS
- Allowed: lifecycle domain module, tests, exports
- Forbidden: current-state backfill, deletion of delisted identities, universe engine
- Input: effective-dated lifecycle facts
- Output: immutable point-in-time listing lifecycle
- Tests: before listing, active interval, delisting date/boundaries, invalid chronology
- Acceptance: pre-listing/post-delisting cannot be tradable and history remains queryable
- Risk: HIGH (Point-in-Time/survivorship)
- Commit: `feat(domain): model listing lifecycle`

### P01-M1.4-T1 — Historical ST and trade status

- Phase/Milestone: Phase 1 / M1.4
- Goal: model effective-dated `STStatus` and `TradeStatus` histories with non-overlap validation and explicit as-of lookup.
- Dependencies: M1.3 PASS
- Allowed: status domain module, tests, exports
- Forbidden: replacing history with current status, silently filling temporal gaps, execution/matching semantics
- Input: effective-dated status intervals
- Output: deterministic historical status queries
- Tests: transitions and boundaries, suspension, gaps, overlaps, current-state contamination regression
- Acceptance: historical switches are correct; unknown history fails closed; current status cannot overwrite the past
- Risk: HIGH (Point-in-Time)
- Commit: `feat(domain): add historical trade status`

## Verification

Task/Milestone checks remain focused. High-risk M1.2–M1.4 require boundary, anti-leakage, deterministic, and invalid-history regression coverage. At the Phase Gate, run one `make verify` closure because it already aggregates lint, type, tests, and evals.

## Offline and scope boundary

No network, Provider, brokerage, account, browser automation, live market query, or order side effect. Models accept explicit local facts and fail closed when historical knowledge is absent.

## Phase gate

- All four Milestone Reviews PASS.
- Domain objects have type/behavior tests.
- TradingCalendar is usable by later local data modules without assuming weekdays are exchange truth.
- Listing, ST, and trade statuses use explicit Point-in-Time semantics and retain history.
- One non-duplicative `make verify` closure passes.
- Evidence and residual risks are recorded before archival.

## Evidence

Pending implementation and review.
