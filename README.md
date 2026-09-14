# Gold Scanner V6

V6 is focused on entry timing.

## Main changes
- One entry zone only.
- Red zone is drawn directly over the uploaded M5 screenshot.
- Final states:
  - WAIT FOR ZONE
  - WAIT FOR CONFIRMATION
  - ENTRY READY BUY
  - ENTRY READY SELL
  - WAIT
  - REFRESH H1/M15
- No TP or SL is generated.
- H1/M15 freshness protection remains.
- M5 rescans are price/confirmation triggered, not timer triggered.

## Update
Replace these files in GitHub:
- server.py
- index.html
- sw.js
- manifest.json
- icon.svg

Then redeploy the latest commit on Render.

The visual band is approximate because Gemini estimates its vertical position from the screenshot.
