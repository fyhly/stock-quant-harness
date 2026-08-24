# System Architecture

## Scope and principles

The system is an offline A-share research pipeline:

```text
Data → Universe → Factors → Portfolio → Backtest → Report
```

Each layer consumes versioned local artifacts through an explicit interface and
emits deterministic, auditable artifacts. Dependencies flow only to the right;
reports do not alter simulations and research outputs do not cause orders. V1
contains no broker, account, credential, order-routing, or live-execution layer.

## Layer responsibilities

### Data

Stores immutable Raw Artifacts and produces validated, normalized datasets.
Provenance includes source, retrieval/version identity, schema, and checksums.
Normalization preserves source observations, corrections, announcement times,
and corporate-action history instead of overwriting them with the latest view.

### Universe

Resolves the securities eligible at a requested decision timestamp. It uses
point-in-time listings, delistings, index membership, ST status, suspensions, and
other eligibility data. It never derives a historical universe from today's
survivors.

### Factors

Computes features from Data and Universe snapshots using declared lookback,
availability, and decision times. Fitting and normalization parameters belong
to a specific training window. Labels are separated from feature inputs and may
not cross the decision-time boundary.

### Portfolio

Transforms timestamped signals into target holdings under declared capital,
exposure, turnover, concentration, lot-size, and risk constraints. Targets are
research intent, not executable orders.

### Backtest

Simulates the transition from targets to holdings using an explicit trading
calendar and execution model. It accounts for signal availability, order time,
fill time, T+1, suspensions, price limits, lot sizes, fees, taxes, corporate
actions, and rejected/unfilled intent. Unsupported semantics fail closed.

### Report

Reads immutable run artifacts to produce performance, risk, attribution, data
quality, and assumption disclosures. A report identifies code, configuration,
input-data versions, universe snapshot policy, and evaluation windows. It is a
research artifact and has no execution side effect.

## Time semantics

Time is part of every layer's interface rather than an implicit index.

- **event time**: when the represented economic or market event occurred;
- **availability time**: when a researcher could first know the observation,
  such as an exchange publication or financial announcement timestamp;
- **effective time**: when a status, membership, or corporate action applies;
- **decision time**: the cutoff for information used to form a signal/target;
- **order time**: when the simulation submits intent after the decision;
- **fill time**: when the modeled market rules permit execution;
- **ingestion time/version**: when and as which artifact the system recorded it.

For a decision at `t`, every feature input must have availability time at or
before `t`. Effective time alone does not prove availability. A fill cannot use
the same bar's closing value when that value was unknown at order time. Trading
dates use an explicit exchange calendar and timestamps use declared time zones;
date-only values must state their market-session convention.

## Artifact and dependency boundaries

```text
immutable raw data
  └─ normalized, versioned data
       └─ point-in-time universe snapshot
            └─ timestamped factor artifact
                 └─ target portfolio artifact
                      └─ backtest run artifact
                           └─ read-only report artifact
```

Artifacts carry schema/version identifiers and content or manifest checksums.
A run manifest pins all upstream identities plus code revision and configuration.
Caching keys include time semantics and upstream versions. Missing provenance,
ambiguous timestamps, or unavailable inputs stop the pipeline rather than
falling back to current or network data.

## Research and execution separation

The repository produces hypotheses, target portfolios, simulated fills, and
reports only. There is no path from Portfolio or Report to a brokerage system.
External data acquisition, once authorized in its later phase, terminates at
immutable Raw Artifacts; normal research remains reproducible without network
access. Human users independently own all real trading decisions and actions.
