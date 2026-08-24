# Phase 10 — First Real A-share E2E Audit

Status: PASS — RESEARCH ONLY. This is not investment advice and is not a live-trading result.

## Source and immutable data identities

- Source: Eastmoney public HTTPS daily-kline response, acquired once at `2026-08-24T11:57:19Z`.
- Query: `klt=101`, `fqt=0` (unadjusted), `beg=20230101`, `end=20241231`, official response fields `f51..f61`.
- Securities: `600000.XSHG` and `000001.XSHE`.
- Shanghai raw SHA-256: `2659fa363faa1dd2ffc135a4475b48c67998ea2f84168ce32865aeb1922fa503`.
- Shenzhen raw SHA-256: `cbb2b85e7d7118e4a244cfe56bf3885eb0a7a4d6cb45911ef80a082fb87f4351`.
- Normalized Parquet SHA-256 / data identity: `225f34963ad07a8b7db8e5aef9fd0bf888b480dc6737f1750a878d80809434bf`.
- Schema: `eastmoney-kline-f51-f61-v1` → `real-bars-v1`; 968 unique ordered rows; volume converted from lots to shares only when loaded.

The complete URLs, query maps, fetch timestamps, raw filenames and hashes are in `tests/fixtures/real/v1/manifest.json`. Exact source bytes remain in the two adjacent JSON files.

## Configuration and code identities

- Run config: `tests/fixtures/real/v1/run-config.json`.
- Config SHA-256: `96f2b87a54dad4bfc1ca80600484757ba6de2cab3ad24e190f836f85037b95d4`.
- Pinned implementation Git commit: `db7ec5eec44e311d7fe439954dcf53db96943848` (M10.5).
- Git identity SHA-256: `13d4f979fc933cf1a3b5ca47cb25e7a43503963469d16df54e05cd568511879c`.

## Pipeline, quality, and result

The offline path is Raw → fixed Parquet → historical Universe → 20-session momentum and volatility → monthly-close top-1 selection → 80% target / 20% cash → RiskDecision → next-session raw-open execution.

- Decision: `2024-11-29` close; fill: `2024-12-02` raw open.
- Selected/fill: `000001.XSHE`, 7,000 shares at raw `11.39`.
- Commission: `23.92`; ending cash: `20246.08`; ending equity: `99976.08`.
- Backtest fingerprint: `b6b4be7b4917c65f6ba03cca6a4a1f231266034dbc39803a80dfa3fc2fca1e96`.
- Quality: raw hashes verified, OHLC invariants valid, no duplicate keys, no negative volume, exact offline reload, no decision-day close in features, no same-day fill, and repeated result equality.

## Explicit limitations

This two-name sample is intentionally tiny and is not representative of the A-share market. Frozen listing, normal/ST, trading-status, sample-index and sector facts exist only to close the bounded research fixture and are not claims about a production index universe. The run has one rebalance, zero slippage, simplified fixed fees and main-board 10% limits, no corporate actions during the holding interval, no benchmark, no statistical significance and no performance conclusion. Public-source availability and correctness are not guaranteed. The artifact is strictly research-only and must never be used as an execution instruction.
