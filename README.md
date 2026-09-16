# Gold Scanner V18.1 — Landscape HTF + Portrait M5

V18.1 keeps V18's deep multi-timeframe engine and changes the visual workflow to match each timeframe's job.

## Recommended workflow
- H1: landscape screenshot, analyzed/saved for broad structure and major zones.
- M15: landscape screenshot, analyzed/saved for intermediate structure and nearby context.
- M5: fresh portrait screenshot on every scan so recent execution candles, wicks, rejection and local structure are larger.
- Backend: when `TWELVE_DATA_API_KEY` is configured, up to 240 XAU/USD candles are analyzed independently for M5, M15 and H1.
- Gemini combines the fresh M5 visual with saved H1/M15 visual context and deterministic multi-timeframe metrics.
- BUY and SELL cases are evaluated independently; higher timeframes provide context and do not automatically force direction.

## Retained systems
Structure/BOS/CHoCH context, ATR, momentum, volatility, swings, liquidity/equal highs-lows, displacement, imbalance/FVG context, role flips, fake breaks, zone lifecycle/scoring, current-vs-historical confirmation, chase protection, event switch, risk filter, optional sizing estimate, saved HTF context and scan journal.

## Render
Build: `pip install -r requirements.txt`
Start: `gunicorn server:app`

Environment variables:
- `GEMINI_API_KEY` — required
- `GEMINI_MODEL` — optional, defaults to `gemini-3.6-flash`
- `TWELVE_DATA_API_KEY` — optional; enables deeper deterministic OHLC analysis

This is an analysis/testing tool, not an automated trading system. Evidence scores are not win probabilities. Demo/forward-test before live use.
