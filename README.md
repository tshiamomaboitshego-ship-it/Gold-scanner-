# Gold Scanner V20 — Testing & State Engine

V20 keeps V19 protection and adds a measurement layer instead of piling on indicators.

## New in V20
- Closed-candle deterministic diagnostics.
- Reaction-quality and wick-rejection metrics.
- Persistent setup memory/journal (last 100 scans).
- Deterministic zone outcome tracker: NOT_TRIGGERED / TESTED / REACTED / INVALIDATED.
- Outcome tracking filters OHLC to candles after each saved prediction timestamp.
- Quota-free recent M5 replay diagnostics for pressure, phase, structure and shock states.
- Phone testing-lab controls in the UI.
- Existing V19 shock, approach-speed, chase, HTF refresh, AI/data conflict, zone lifecycle and evidence decomposition retained.

## Important limitations
- Outcome tracking measures zone behavior, not trade profitability or win probability.
- Replay currently validates deterministic market-state logic; it is not yet a full historical Gemini screenshot replay or a profit backtest.
- Automatic economic-calendar integration is NOT included. Manual event mode + volatility-shock protection remain.
- Deep OHLC and testing lab require `TWELVE_DATA_API_KEY`.
- Gemini analysis requires `GEMINI_API_KEY`.

## Deploy
Put all files at the GitHub repository root. Render build: `pip install -r requirements.txt`. Start: `gunicorn server:app`.
