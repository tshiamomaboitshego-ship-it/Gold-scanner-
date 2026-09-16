# Gold Scanner V17 — Saved HTF Context

V17 adds saved H1 + M15 chart context to the V16 hybrid M5 scanner.

## Workflow
1. Upload H1 once and tap Analyze + save H1.
2. Upload M15 once and tap Analyze + save M15.
3. Upload fresh M5 screenshots for normal scans.
4. V17 sends the saved compact H1/M15 analysis with each M5 scan; it does not re-send or re-analyze the old H1/M15 screenshots.
5. Refresh H1/M15 when the UI warns that context is stale or the saved structural refresh condition occurs.

## Quota behavior
- H1 analysis = one Gemini request when you explicitly save/refresh it.
- M15 analysis = one Gemini request when you explicitly save/refresh it.
- Each M5 scan = one Gemini request.
- No automatic retry loop.
- Screenshots are not stored in localStorage; only compact JSON context is saved.

## Context roles
H1 supplies broad structure and major zones. M15 supplies intermediate structure and nearby zones. M5 remains the execution timeframe. Higher-timeframe context adds evidence and conflict awareness but does not automatically veto M5.

## Existing V16 systems retained
Real M5 OHLC support, deterministic swings, HH/HL and LL/LH, BOS/CHoCH, ATR, momentum, displacement, FVG context, role flips, fake breaks, zone lifecycle, chase protection, risk filtering, session context and journal.

## Environment variables
- GEMINI_API_KEY (required)
- GEMINI_MODEL (optional, defaults to gemini-3.6-flash)
- TWELVE_DATA_API_KEY (optional; enables exact M5 OHLC analytics)

Analysis aid only. Demo-test before considering live use.
