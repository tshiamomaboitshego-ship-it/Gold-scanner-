# Gold Scanner V27 Live

Screenshot-free XAU/USD scanner.

## Normal workflow
Press **SCAN LIVE MARKET**. The server fetches Twelve Data H1, M15 and M5 OHLC plus a separate reference price, then the deterministic Python engine maps candidate zones.

Both setup families run every scan:
- PULLBACK CONTINUATION
- NEW MOVE ORIGIN

No screenshot or Gemini request is used by `/api/live-scan`. Existing hybrid `/api/scan` remains in the server for compatibility, but the V27 UI does not use it.

## Render
Build: `pip install -r requirements.txt`
Start: `gunicorn server:app`
Required env: `TWELVE_DATA_API_KEY`
`GEMINI_API_KEY` is not required for normal V27 live scanning.

The scanner is an analysis aid. Candidate zones and scores are not predictions or win probabilities.
