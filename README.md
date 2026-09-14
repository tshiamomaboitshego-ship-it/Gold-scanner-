# Gold Scanner V6.4 — Momentum Fix

Fixes:
- Separates H1/M15 bias from current M5 momentum.
- Can show SELL bias while M5 is in a bullish pullback.
- Will not mark an entry READY while M5 is strongly moving against the intended direction.
- Uses WAIT CONFIRMATION until M5 aligns again.
- Rejects TP targets that overlap active entry zones.
- Tightens entry bands and shrinks labels so candles stay visible.
- Still maps up to 3 entry opportunities in one Gemini request.
- Exact same M5 screenshot still uses cached result with zero new request.

Replace in GitHub/Render:
- server.py
- index.html
- sw.js

Then redeploy Render.
