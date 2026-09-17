# Gold Scanner V21 — Price-Action Confluence Engine

V21 keeps V20 testing/protection and adds deterministic price-action confluence:

- order-block / breaker-block heuristic
- FVG quality + fill-state tracking
- liquidity sweep → structure → FVG sequence recognition
- premium / equilibrium / discount context
- internal vs external liquidity
- cautious inducement context through Gemini (only when clear)
- session highs/lows + simple London/New York opening ranges from OHLC
- closed-candle body acceptance vs wick sweep/reclaim
- confluence clustering with supporting and opposing evidence
- V20 setup tracking, outcome checks and deterministic replay retained

These are evidence features, not guaranteed signals. V21 deliberately avoids treating a single FVG, order block, liquidity level, premium/discount state, or session level as an automatic BUY/SELL rule.

## Environment
- GEMINI_API_KEY required for screenshot analysis.
- GEMINI_MODEL optional; defaults to gemini-3.6-flash.
- TWELVE_DATA_API_KEY strongly recommended for deterministic M5/M15/H1 OHLC features.

Automatic economic-calendar integration is still not included; use the manual high-impact-event switch. Volatility-shock protection remains active when OHLC is connected.
