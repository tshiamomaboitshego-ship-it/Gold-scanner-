# Gold Scanner V13 — M5 Pullback Finder

Focused screenshot scanner for XAUUSD M5. It maps fresh BUY and SELL pullback areas from visible recent structure and tells the user what reaction to wait for. It does not issue automatic entries or TP levels.

## Render
Build: `pip install -r requirements.txt`
Start: `gunicorn server:app`
Environment: `GEMINI_API_KEY`
Optional: `GEMINI_MODEL` (default `gemini-3.6-flash`) and `GEMINI_FALLBACK_MODEL` (default `gemini-3.5-flash`).

V13 makes at most one controlled fallback request when the primary model returns 503/high demand or 429/resource exhausted. It never loops retries.
