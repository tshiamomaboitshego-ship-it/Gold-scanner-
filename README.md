# Gold Scanner V16 Advanced

Phone-first XAUUSD M5 analysis aid. V16 extends V15 with deterministic OHLC context plus conservative AI chart interpretation.

## V16 additions
- Zone lifecycle: fresh/testing/reacted/retested/consumed/invalidated/expired
- Displacement and recent FVG/imbalance context
- Support/resistance role-flip and fake-break/reclaim context
- ATR-relative extension/chase filter
- Session context
- Spread/cost input
- Setup-conflict detection
- Strongest-zone-only output
- Optional educational position-size estimate using balance, risk %, SL distance and broker contract size
- Journal remains local on the phone/browser
- Historical reaction remains separated from current confirmation

## Existing core
Real XAU/USD M5 OHLC when `TWELVE_DATA_API_KEY` is configured, swing structure, HH/HL and LL/LH, BOS/CHoCH, ATR, momentum, equal-high/low context, break/retest analysis, evidence scoring, event-risk switch, risk filter.

## Render
Build: `pip install -r requirements.txt`
Start: `gunicorn server:app`
Environment: `GEMINI_API_KEY`, optional `GEMINI_MODEL`, optional `TWELVE_DATA_API_KEY`.

## Important limitations
Automatic economic-calendar/news ingestion is NOT included; the high-impact event switch remains manual. The app does not know your broker's live spread or exact contract specification unless you enter them. Journal data is local and does not yet automatically label future trade outcomes. Evidence scores are not win probabilities. Demo/forward testing is required before drawing performance conclusions.
