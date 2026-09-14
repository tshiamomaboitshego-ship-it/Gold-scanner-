# Gold Scanner V6.6.1 — Quota-safe confirmed entry fix

This fixes the V6.6 issue where a scan could finish loading without showing a result.

Main protections:
- hard one-tap lock: repeated taps cannot send another request while a scan is running
- same M5 screenshot is checked against local cache BEFORE any AI request
- a successful AI result is saved BEFORE UI/overlay rendering
- if the overlay fails, the text result still appears
- every scan ends in a visible state:
  - ENTRY READY BUY
  - ENTRY READY SELL
  - NO CONFIRMED ENTRY
  - REFRESH H1/M15
  - or a clear SCAN ERROR
- no automatic retries after quota/rate-limit errors
- missing H1/M15/M5 is caught locally and uses zero AI requests
- service-worker cache version bumped so the phone receives the fixed frontend

Deploy:
1. Replace `server.py`, `index.html`, and `sw.js` in GitHub.
2. Redeploy latest commit on Render.
3. On the phone, reload the page. If the old UI remains, close the installed PWA/tab and reopen it once.

Use one fresh M5 screenshot for the first test.
