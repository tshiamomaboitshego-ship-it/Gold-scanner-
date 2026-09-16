# Gold Scanner V15 Hybrid

V15 adds the next architecture layer without pretending a scanner can be perfect.

## Implemented now
- Optional real XAU/USD 5-minute OHLC via Twelve Data (`TWELVE_DATA_API_KEY`).
- Deterministic ATR14 volatility, momentum, fractal swing highs/lows, HH/HL vs LL/LH structure, BOS/CHoCH checks, and equal-high/low context.
- Gemini screenshot analysis used as a second analyst, not the only analyst.
- Freshness/zone evidence scoring (not win probability).
- Break-and-retest context and liquidity context.
- Strict fresh-confirmation states. `HISTORICAL_REACTION` is separate from `CURRENT_CONFIRMATION`.
- Manual high-impact-news switch that blocks confirmation mode during event risk.
- Risk filter plus optional demo risk budget display.
- Text-only scan journal stored on the phone/browser (last 100 scans; images are never stored in localStorage).
- Current-price preference from live OHLC when connected; screenshot label is fallback.

## Render setup
Keep existing `GEMINI_API_KEY` and `GEMINI_MODEL`.
Optional but recommended: create a Twelve Data API key and add `TWELVE_DATA_API_KEY` in Render environment variables. Without it, V15 still runs in screenshot-only mode and clearly labels that limitation.

## Still requires real testing
The scanner cannot honestly claim improved profitability until the journal contains enough historical/demo/forward observations. Test 50–100+ setups first. News awareness is manual in this build; automatic economic-calendar integration needs a separate reliable calendar source/API.

## Important
`CURRENT_CONFIRMATION` means the newest visible/data-supported setup met the scanner's evidence rules. It is not a guaranteed trade or automatic entry.
