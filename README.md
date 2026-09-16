# Gold Scanner V19

Phone-first XAUUSD analysis scanner. H1/M15 landscape context + fresh M5 portrait execution view.

## V19 additions
- Current M5 pressure separated from future pullback zones
- Deterministic market-phase classification
- Closed-candle volatility shock detector
- Approach-speed detection
- Automatic volatility pause and HTF refresh warning after extreme displacement
- AI-vs-OHLC conflict field
- Setup memory passed from recent journal scans
- Evidence score component support
- Existing V18.1 deep M5/M15/H1 OHLC, structure, ATR, momentum, liquidity, FVG, role-flip, chase filter and zone lifecycle retained

## Environment variables
- `GEMINI_API_KEY` required
- `GEMINI_MODEL` optional, defaults to `gemini-3.6-flash`
- `TWELVE_DATA_API_KEY` optional but strongly recommended for deterministic M5/M15/H1 OHLC

## Important limitation
V19 does **not** pretend to have a live economic-calendar feed. The manual high-impact-event switch remains. V19 adds a deterministic volatility-shock fallback so abnormal closed-candle movement can pause normal zone logic even when the event switch was missed. A future version can add a verified calendar provider/API.

Analysis aid only. Demo-test before any real-money use.
