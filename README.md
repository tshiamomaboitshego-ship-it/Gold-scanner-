# Gold Scanner V26 — Opportunity Engine

V26 keeps the V25.1 Twelve Data lifecycle fix and expands the scanner beyond pullbacks.

## Normal workflow
1. Upload one fresh portrait XAUUSD M5 screenshot.
2. The server automatically fetches H1, M15 and M5 OHLC from Twelve Data.
3. Python maps areas ahead of current price for two setup families:
   - PULLBACK_CONTINUATION
   - NEW_MOVE_ORIGIN
4. BUY watch areas are normally below current price and SELL watch areas above current price.
5. H1/M15 confluence can strengthen or weaken M5 candidates without forcing direction.
6. Lifecycle/confirmation is tracked separately: a watch area is not a prediction or an entry signal.
7. When Gemini is available, one M5 visual call acts as a second opinion. If quota is exhausted, DATA_ONLY mode keeps the OHLC opportunity map active.

## V26 changes
- Current-price anchored opportunity mapping.
- New-move-origin candidates around meaningful range extremes and liquidity pools.
- Pullback continuation candidates retained.
- Ranging/reversal-developing phases can prioritize range/liquidity extremes rather than the middle.
- Candidate output includes setup_type, current_price_relevance, opportunity_score and opportunity_reason.
- UI renamed BUY/SELL PULLBACK AREA to BUY/SELL WATCH AREA.
- Existing V25.1 M5-specific OHLC lifecycle fix retained.

## Environment
- `TWELVE_DATA_API_KEY` — required for live H1/M15/M5 OHLC.
- `GEMINI_API_KEY` — required for hybrid visual mode.
- `GEMINI_MODEL` — optional; defaults to `gemini-3.6-flash`.

Build: `pip install -r requirements.txt`
Start: `gunicorn server:app`

This is an analysis/testing aid. Ahead-of-price watch areas are evidence locations, not guarantees that price will reverse or continue there.
