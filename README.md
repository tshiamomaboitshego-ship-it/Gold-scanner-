# Gold Scanner V22 — Lifecycle & Timing Engine

V22 is built on V21 and focuses on the failure found during live testing: a useful level could be labelled FRESH even after price had already touched and reacted from it.

## V22 upgrades
- Deterministic closed-candle zone lifecycle reconciliation from live M5 OHLC.
- Timing states: UNTESTED, ACTIVE_TEST, ALREADY_REACTED, RETEST_PENDING, INVALIDATED.
- Recently touched/rejected zones are no longer presented as fresh first-touch setups when live OHLC can verify the touch.
- `NO_ACTIVE_SETUP` is separated from future mapped BUY/SELL locations.
- Distance to each zone and ATR-normalized distance are shown.
- Evidence-score components are surfaced in the phone UI when supplied.
- Current pressure/market phase remain separate from future zones.
- V21 confluence engine remains: market structure, BOS/CHoCH, liquidity, FVG quality, order blocks/breakers, premium/discount, session liquidity, displacement, acceptance/rejection and sequence recognition.
- V20/V19 testing, outcome tracking, volatility-shock, approach-speed, chase and AI/data conflict protections remain.

## Important
This is an analysis/testing aid, not an automatic trading system and not a profitability guarantee. Automatic economic-calendar integration is still not included. Manual event-risk mode and deterministic volatility-shock protection remain.

For deterministic lifecycle/timing, configure `TWELVE_DATA_API_KEY`. Gemini screenshot analysis requires `GEMINI_API_KEY`.
