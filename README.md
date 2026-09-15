# Gold Scanner V9 — M5-only Entry Scanner

V9 removes H1 and M15 from the workflow.

Workflow:
M5 screenshot → one AI request → BUY SETUP / SELL SETUP / NO TRADE → one fresh entry zone → invalidation → TP1/TP2/TP3.

The model is explicitly instructed not to infer higher-timeframe bias. It focuses on current price and recent M5 structure only.

Freshness protections remain:
- rejects used/missed historical zones
- rejects a setup if current price has already progressed to/past TP1
- no confirmation rescan
- no automatic retry
- image remains in temporary browser memory
- same exact M5 can use cached JSON result

Important: M5-only removes higher-timeframe influence, but it does not guarantee better trading performance. Test before relying on it with live money.

Deploy server.py, index.html, sw.js and manifest.json, then confirm the page says Gold Scanner V9.
