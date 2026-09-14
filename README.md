# Gold Scanner V6.6 — Confirmed Entry Mode

Main change:
Potential future areas are no longer called entries.

The scanner now returns:
- ENTRY READY BUY
- ENTRY READY SELL
- NO CONFIRMED ENTRY
- REFRESH H1/M15

H1/M15 provide context. M5 controls the actual entry.

If no current M5 confirmation exists:
- scanner says NO CONFIRMED ENTRY
- possible future areas are labeled WATCH, not ENTRY
- TP levels are hidden because there is no actionable trade yet

If M5 confirms:
- ONE precise CONFIRMED ENTRY is shown
- TP1/TP2/TP3 are shown only if valid
- hard server validation blocks opposite-M5 READY signals and invalid targets

Still:
- up to 3 WATCH areas
- one Gemini request per fresh M5
- same M5 screenshot cache
- H1/M15 freshness checks

Replace in GitHub/Render:
server.py
index.html
sw.js

Then redeploy.
