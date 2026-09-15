# Gold Scanner V8.2 — Image Ready Fix

V8.2 keeps V8.1's fresh-entry trading logic unchanged and fixes the phone image-loading problem.

Before Scan is enabled:
- H1 must show ✅ H1 ready
- M15 must show ✅ M15 ready
- M5 must show ✅ M5 ready

Images are fully read and verified immediately when selected. The Scan button stays disabled until all three are in memory. No FileReader operation happens after pressing Scan, removing the failure that previously produced "Could not read image".

Quota protection:
- image errors happen before Gemini and use zero requests
- exactly one frontend `/api/scan` fetch
- exactly one scan handler
- double-tap lock
- same-M5 cache checked before Gemini
- successful result cached before rendering
- no automatic retries

Deploy server.py, index.html, sw.js, manifest.json and redeploy Render.
Make sure the page says Gold Scanner V8.2.
