# Gold Scanner V24 — One Screenshot Hybrid

Normal workflow: upload ONE fresh M5 screenshot. The backend automatically fetches XAU/USD H1, M15 and M5 OHLC from Twelve Data and runs the deterministic Python engine. Gemini receives only the M5 screenshot plus compact OHLC metrics as a visual second opinion.

## Render environment
- `GEMINI_API_KEY`
- `GEMINI_MODEL` optional, default `gemini-3.6-flash`
- `TWELVE_DATA_API_KEY`

## V24 changes
- H1/M15 screenshot uploads removed from normal UI.
- `/api/ohlc-test` tests H1/M15/M5 Twelve Data without using Gemini quota.
- H1/M15/M5 exact OHLC analyzed automatically.
- Existing deterministic structure, BOS/CHoCH, ATR, momentum, liquidity, FVG quality, premium/discount, order-block heuristics, session context, candidate-zone ranking and consumption logic retained.
- If Gemini returns a quota 429 but OHLC is available, scanner falls back to DATA-ONLY mode rather than becoming unusable.
- Hybrid scan uses one Gemini request per M5 scan under normal operation.

This is an analysis/testing aid, not an automated trading system or guarantee of profitable outcomes.
