# Gold Scanner V29 Intelligence+

Screenshot-free XAU/USD market scanner for Render.

## Core scan
- Twelve Data H1 + M15 + M5 OHLC and separate reference price
- Deterministic Python structure: swings, HH/HL, LL/LH, BOS/CHoCH, FVG/imbalance, order blocks, supply/demand candidates, liquidity/sweeps, displacement, ATR/momentum, premium/discount, zone freshness/touches/consumption
- Independent Pullback Continuation and New Move Origin engines
- Allows NO QUALIFIED AREA instead of forcing a zone

## V29 intelligence upgrades
- Session intelligence: Asia, London, New York highs/lows and opening ranges
- Previous-day high/low/open/close and previous-week high/low/open/close when present in the fetched sample
- Nearest session/day/week liquidity levels and simple sweep/reclaim state
- Historical M5 ATR percentile / volatility regime (LOW, NORMAL, HIGH, EXTREME)
- Provider volume/tick-volume context when actually supplied; if absent, V29 says unavailable and does not invent volume
- USD/DXY context where Twelve Data exposes it
- FRED US 2Y, 10Y and 10Y real-yield context when `FRED_API_KEY` is configured
- Optional gold-futures context via `GOLD_FUTURES_SYMBOL`; the scanner intentionally does not guess a provider symbol
- Forward Test Lab remains on-device

## Environment variables
Required:
- `TWELVE_DATA_API_KEY`

Optional:
- `FRED_API_KEY`
- `TRADING_ECONOMICS_KEY` (only if you want automatic calendar data)
- `GOLD_FUTURES_SYMBOL` (only if you have verified a gold-futures symbol supported by your Twelve Data plan)

## Important design rule
Technical XAU/USD price structure creates zones. Session, macro, volatility, volume and futures context may modestly adjust ranking/caution but never invent or move a zone. Evidence scores are not win probabilities.

Render build: `pip install -r requirements.txt`
Render start: `gunicorn server:app`
