# Gold Scanner V8 — One-Scan Entry Finder
Upload H1 + M15 + M5 once. It returns BUY SETUP, SELL SETUP or NO TRADE; ONE best entry zone; entry instruction; invalidation; and TP1/TP2/TP3 when valid.

There is no watch-zone/rescan loop. Existing quota protections remain: one scan handler, one API fetch, double-tap lock, same-M5 cache before Gemini, no automatic retries.

Deploy server.py, index.html, sw.js and manifest.json, redeploy Render, and confirm the page says Gold Scanner V8 before scanning.
