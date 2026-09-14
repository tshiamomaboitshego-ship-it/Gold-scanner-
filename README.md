# Gold Scanner V6.1 — Entry + TP Zones

Changes:
- Keeps the visual entry-zone band on the uploaded M5 screenshot.
- Adds TP1, TP2 and TP3 based on visible market structure.
- Draws TP lines directly on the chart when Gemini can locate them.
- Keeps entry timing states: WAIT FOR ZONE, WAIT FOR CONFIRMATION, ENTRY READY BUY/SELL, WAIT, REFRESH H1/M15.
- H1/M15 freshness protection remains.
- Stop loss is left to the trader.
- Gemini 429/free-quota errors are now shown as a short friendly message instead of the full technical error.

Replace server.py, index.html and sw.js in GitHub, then redeploy Render.
