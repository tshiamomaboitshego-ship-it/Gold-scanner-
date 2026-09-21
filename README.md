# Gold Scanner V39.1 — M1-First Precision Quant Engine

Built from V38.1. Adds five focused precision upgrades while retaining the forward-only Quant Engine:

- Mathematical confluence / level clustering across independent structural families.
- Impulse/pullback geometry scoring from closed M1 OHLC.
- ATR-bounded micro-zone refinement inside existing structural zones only.
- Liquidity target path + opposing obstacle analysis.
- Evidence redundancy control so correlated BOS/FVG/OB-style evidence is not over-counted.

Existing freshness, used-zone suppression, candidate competition, pullback quality, TPO/session context and Quant MFE/MAE/reaction tracking remain active. VWAP/AVWAP are still optional and are not fabricated when trustworthy volume is unavailable.

This is a forward-test build. Precision scores and Quant reaction statistics are evidence, not probabilities or guarantees.


## V39.1 M1-FIRST architecture
- M1 owns setup detection, candidate generation, structural qualification, mathematical clustering, micro-zone refinement and precision-point output.
- M5, M15 and H1 retain their structure/concept analysis and can add bounded confluence/context to ranking, but cannot veto an otherwise legitimate M1 candidate.
- Higher-timeframe disagreement is labeled ALIGNED / MIXED / COUNTER_CONTEXT; it does not raise the M1 qualification threshold.
- The old counter-context pre-filter was removed.
- The M1 structural qualification floor is no longer selected from M5-heavy context.
- Quant tracking, freshness/consumption, liquidity path, pullback geometry and evidence-redundancy controls remain active.
