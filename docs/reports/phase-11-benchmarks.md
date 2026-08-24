# Phase 11 Fixed Benchmark Report

Status: RESEARCH ONLY. These predefined sanity benchmarks are not investment advice, parameter searches, winner selection, or out-of-sample evidence.

All configurations are reported: momentum 20/60/120 sessions; reversal 5/10 sessions with negative-return sign; low-vol 20 sessions with realized and downside volatility annualized by 252; value ranked by announcement-available earnings yield; quality ranked by announcement/revision-available ROE; and technical MA20-above-MA60 plus prior-close breakout over the preceding 20 sessions.

Every input uses an explicit decision cutoff. Technical signals exclude the decision bar and become eligible only on the next injected trading session. Missing, gapped, future, stale, invalid-denominator, and future-restatement cases remain visible as explicit failures or undefined scores; they are never repaired or removed from reporting to improve results.

The library deliberately reports scores/signals and explanations rather than choosing a best benchmark. No claim of profitability, robustness, generalization, or OOS performance is made.
