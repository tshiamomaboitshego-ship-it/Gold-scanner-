# Gold Scanner V14 — Pullback + Confirmation Finder

Phone-friendly XAUUSD M5 screenshot analyzer.

V14 changes:
- Conservative confirmation states: WAIT, TESTING, REJECTION DETECTED, CONFIRMATION DEVELOPING, CONFIRMED, INVALIDATED.
- Evidence score for each zone (0–100). This is **not** a win probability.
- Structure classification (HH/HL, LL/LH, mixed) and volatility flag.
- Current price must come from a clearly readable right-edge price label; otherwise it returns null.
- No automatic retry/fallback request, to protect free Gemini quota.
- No BUY NOW / SELL NOW instruction and no TP prediction.

Render setup stays the same: `pip install -r requirements.txt` then `gunicorn server:app`. Keep `GEMINI_API_KEY` and optionally `GEMINI_MODEL=gemini-3.6-flash` in environment variables.

Important: V14 is still screenshot-based. Exact OHLC market-data integration and statistical validation require a reliable data source and are separate future upgrades. Test V14 on demo and log at least 50–100 setups before considering real-money use.
