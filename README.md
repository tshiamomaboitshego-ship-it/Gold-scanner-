# Gold Scanner V30 — Final Test Build

Final feature-frozen test build. Screenshot-free normal scanning.

## Core
- H1/M15/M5 deterministic XAU/USD structure, BOS/CHoCH, liquidity, sweeps, FVG/imbalance, OB/breakers, supply/demand, displacement, premium/discount, role flips, fake breaks/reclaims.
- Independent Pullback Continuation and New Move Origin engines; no forced BUY/SELL area.
- Session liquidity, previous day/week levels, volatility regime and provider volume when genuinely supplied.
- Optional DXY, FRED Treasury/real-yield context and GOLD_FUTURES_SYMBOL.
- Weekly CFTC managed-money positioning is fetched as slow context only; never an M5 trigger.
- Manual high-impact event switch remains the preferred event workflow if no calendar key is configured.

## V30 engineering / testing
- Rate-limit protection: H1 ~50 min cache, M15 ~12 min, M5 ~4 min, reference price ~1 min; stale-cache fallback on provider errors/429.
- DXY/futures/FRED/CFTC are cached separately to avoid wasting free API credits.
- Market/data-feed inactive detection prevents old closed candles from looking live.
- Forward-test lab stores frozen zones on-device and grades later zone behavior with NOT_TRIGGERED/TESTED/REACTED/INVALIDATED plus MFE/MAE and setup-type summaries.
- Evidence score remains evidence/ranking, not probability.

## Render env vars
Required: `TWELVE_DATA_API_KEY`
Optional: `FRED_API_KEY`, `GOLD_FUTURES_SYMBOL`, `TRADING_ECONOMICS_KEY`, `GEMINI_API_KEY` (hybrid legacy endpoint only).

Build: `pip install -r requirements.txt`
Start: `gunicorn server:app`

This is an analysis/forward-testing aid, not automated execution or a guarantee of profit.
