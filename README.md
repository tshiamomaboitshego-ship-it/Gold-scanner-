# Gold Scanner V40 — Pullback-Only Intelligence

Built from the verified V39.5 Candidate Ladder + Diagnostics baseline.

## Mission
One job only: identify clean XAUUSD continuation pullbacks and reject poor/failing retracements.

## Kept because they directly help pullbacks
- M1 trend / swing structure
- meaningful impulse detection
- active pullback detection
- retracement depth
- fresh/consumed structural zones
- FVG / order-block / swing / broken-structure retest evidence
- Candidate Ladder: WATCH vs QUALIFIED
- rejection / reclaim / continuation confirmation
- invalidation and trap/failure detection
- ATR-relative volatility
- liquidity/path obstacles and room for continuation
- diagnostics and forward tracking
- M5/M15/H1 as non-blocking context only

## Added in V40
- Pullback Quality: CLEAN / GOOD / MESSY / FAILING
- Depth: SHALLOW / HEALTHY / DEEP / DANGEROUS
- Pullback speed vs preceding impulse speed
- Opposing-candle pressure
- Pullback lifecycle
- Explicit FAILED PULLBACK state
- Continuation-restart detection
- Chase protection context
- Candidate scoring adjusted by pullback quality/failure risk

## Removed from entry generation
- New Move Origin candidates
- local/range origin entry candidates
- independent transition/reversal entry route
- transition/reclaim points that are not part of the active continuation pullback

Internal structure/liquidity calculations may remain where they help determine whether a pullback is healthy or failing; they do not create unrelated entries.

No score is a guarantee or probability of profit.
