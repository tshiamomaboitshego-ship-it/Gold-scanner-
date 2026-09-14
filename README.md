# Gold Scanner V6.2 — Quota Saver

Main change: ONE Gemini request per new M5 scan.

How it works:
1. Upload H1 and M15 once. They are saved on the device.
2. Upload a fresh M5.
3. Tap Scan Full Setup.
4. One Gemini request returns direction, entry timing, entry-zone overlay and TP1/TP2/TP3.
5. If you accidentally scan the exact same M5 screenshot again, V6.2 shows the cached result and uses ZERO new Gemini requests.

Other changes:
- Correctly distinguishes a daily free quota from a temporary rate limit.
- Keeps H1/M15 staleness protection (M15 30 min, H1 60 min).
- Shows approximate local AI-scan count for the current device/day.
- Keeps entry-zone and TP visual marks.
- Stop loss remains user-managed.

Update GitHub:
- server.py
- index.html
- sw.js
Then redeploy Render.
