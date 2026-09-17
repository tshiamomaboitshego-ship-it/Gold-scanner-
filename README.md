# Gold Scanner V25 — One Screenshot Hybrid

Normal workflow: upload ONE fresh M5 screenshot. The backend automatically fetches XAU/USD H1, M15 and M5 OHLC from Twelve Data and runs the deterministic Python engine. Gemini receives only the M5 screenshot plus compact OHLC metrics as a visual second opinion.

## Render environment
- `GEMINI_API_KEY`
- `GEMINI_MODEL` optional, default `gemini-3.6-flash`
- `TWELVE_DATA_API_KEY`

## V25 changes
- H1/M15 screenshot uploads removed from normal UI.
- `/api/ohlc-test` tests H1/M15/M5 Twelve Data without using Gemini quota.
- H1/M15/M5 exact OHLC analyzed automatically.
- Existing deterministic structure, BOS/CHoCH, ATR, momentum, liquidity, FVG quality, premium/discount, order-block heuristics, session context, candidate-zone ranking and consumption logic retained.
- If Gemini returns a quota 429 but OHLC is available, scanner falls back to DATA-ONLY mode rather than becoming unusable.
- Hybrid scan uses one Gemini request per M5 scan under normal operation.

This is an analysis/testing aid, not an automated trading system or guarantee of profitable outcomes.


V25 adds multi-timeframe candidate enrichment: M5 zones are re-ranked using M15/H1 zone overlap, structure context, premium/discount context, depth labels, and deterministic closed-candle confirmation stages. HTF evidence is deliberately a bonus/penalty rather than a directional veto.

## V25.1 lifecycle data fix
- Lifecycle now keys off the actual M5 Twelve Data status, not the all-timeframe aggregate status.
- A temporary H1 or M15 failure no longer forces M5 lifecycle into screenshot-only mode when M5 OHLC is live.
- Twelve Data gets one safe retry per timeframe; this does not use Gemini quota.
- Hybrid scan response exposes per-timeframe data status and whether M5 lifecycle used live OHLC.
