# Gold Scanner V28 Market Intelligence

Screenshot-free XAU/USD analysis engine.

## Core scan
Press **SCAN LIVE MARKET**. V28 fetches Twelve Data H1/M15/M5 OHLC plus a separate XAU/USD reference price. Python creates all technical zones. Both setup families run every scan:
- PULLBACK CONTINUATION
- NEW MOVE ORIGIN

No screenshot or Gemini request is used by `/api/live-scan`.

## V28 intelligence layers
1. **Economic-calendar risk (optional):** Trading Economics US calendar. It can downgrade/caution zones around major releases, but never creates a price zone.
2. **USD + rates context:** attempts DXY/USDX through Twelve Data; optional FRED daily US 2Y, 10Y and 10Y real yields.
3. **Python confluence/regime engine:** existing structure, liquidity, FVG, order-block, displacement, ATR, market-phase, consumption and multi-timeframe logic plus modest macro-context ranking.
4. **Forward Test Lab:** scans are frozen in browser localStorage and `/api/outcomes` grades later M5 zone behavior as NOT_TRIGGERED / TESTED / REACTED / INVALIDATED. These are not win-rate claims.

## Render
Build: `pip install -r requirements.txt`
Start: `gunicorn server:app`

Required:
- `TWELVE_DATA_API_KEY`

Optional intelligence keys:
- `FRED_API_KEY` — FRED daily DGS2, DGS10, DFII10 observations.
- `TRADING_ECONOMICS_KEY` — Trading Economics calendar credentials/key accepted by its `c` parameter.

If optional keys are absent or a provider does not expose a series on the current plan, V28 clearly shows that layer as unavailable and continues with technical analysis. It does not fabricate missing macro data.

Candidate zones and evidence scores are analysis aids, not predictions, probabilities or automatic trade instructions.
