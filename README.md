# Gold Scanner V6.5 — Hard Validation Fix

This version keeps the V6.4 momentum logic and adds SERVER-SIDE validation after Gemini responds.

Main fixes:
- H1/M15 still provide higher-timeframe bias.
- M5 still controls entry timing.
- If SELL bias + bullish M5, a READY sell is automatically downgraded to WAIT CONFIRMATION.
- If BUY bias + bearish M5, a READY buy is automatically downgraded to WAIT CONFIRMATION.
- Every returned entry is mathematically checked against TP1.
- For SELL, TP1 must be meaningfully below the entry zone.
- For BUY, TP1 must be meaningfully above the entry zone.
- An invalid entry is removed automatically.
- TP2/TP3 ordering is checked in code.
- Remaining valid entries are compacted to ENTRY 1 / ENTRY 2 / ENTRY 3.
- If no valid entry remains, signal changes to WAIT instead of showing a false setup.
- The UI can show a short Validation note when the server corrected Gemini output.
- Thin visual entry zones from V6.4 are retained.
- Still one Gemini request per fresh M5 screenshot.
- Exact same M5 screenshot remains cached.

Update GitHub/Render:
Replace:
- server.py
- index.html
- sw.js

Then redeploy Render.
