# Gold Scanner V30.4 — Pullback State Separation

Targeted test build.

Changes from V30.3:
- Pullback market-state detection is now separate from continuation-zone qualification.
- An obvious early M5 retracement can display as PULLBACK_STARTING / PULLBACK_IN_PROGRESS even when no fresh continuation zone qualifies yet.
- State detection cannot manufacture a BUY/SELL zone. Fresh-zone rules remain strict.
- Latest significant impulse/extreme remains recency-first and works symmetrically for bullish and bearish moves.
- Dynamic state now exposes market_state_detected and setup_qualified separately.

All V30.3 fresh-only, caching, macro/session, tracked-setup and forward-test logic is retained.
