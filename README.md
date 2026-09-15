# Gold Scanner V8.1 — Fresh Entry Fix

Fixes the V8 problem where a technically valid historical zone could be returned after the move had already used it.

New logic:
- reads current price from the right edge of M5
- rejects zones already entered/crossed and reacted from
- rejects historical setups if current price has already reached/passed TP1
- does not return a zone simply because it would have worked earlier
- searches for one fresh nearby entry instead
- returns NO TRADE if the move is already gone and no fresh high-quality entry remains
- still one scan only; no watch/rescan loop

Quota protections remain:
- one scan handler
- one API request per fresh uncached M5
- double-tap lock
- same-M5 cache before Gemini
- no automatic retries

Deploy server.py, index.html, sw.js, manifest.json and redeploy Render.
Confirm the page says Gold Scanner V8.1 before scanning.
