# Gold Scanner V6.7 — Clean Confirmed Entry Build

This version is rebuilt from the clean V6.5 base.

Important fixes:
- exactly ONE scan click handler
- exactly ONE `/api/scan` fetch call in `index.html`
- hard double-tap lock while a scan is running
- cache check happens BEFORE any Gemini request
- same exact M5 screenshot reuses saved result with zero Gemini requests
- successful result is cached BEFORE the UI draws it
- no automatic retry on quota/server errors
- actual backend/Gemini error detail is displayed instead of only “Scan failed”
- local validation errors use zero Gemini requests
- service worker cache bumped/cleared to prevent an old frontend from staying on the phone

Entry logic:
- H1/M15 = context
- M5 = actual timing
- possible future levels are WATCH areas
- only current confirmed setup becomes ENTRY READY
- TPs appear only with a confirmed entry

Deploy:
1. Replace `server.py`, `index.html`, `sw.js`, and `manifest.json` in GitHub.
2. Redeploy the latest commit on Render.
3. On phone, close the old scanner tab/PWA completely and reopen the site.
4. If the title does not say `Gold Scanner V6.7`, refresh once before scanning.

First test:
- Upload H1, M15, M5.
- Press `Check Confirmed Entry` ONCE.
- Do not press it again while it says `Checking…`.
