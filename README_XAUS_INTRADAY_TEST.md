# V42.4 XAUS intraday diagnostic

Adds `GET /api/test-xaus-intraday` and a `TEST XAUS INTRADAY` button.

- Requests one hour of XAUS XAU intraday sampled-price data.
- Reports point count, coverage, latest price, data freshness, and simple path direction.
- Does **not** convert sampled prices into OHLC candles.
- Does **not** feed XAUS intraday data into V42 trading decisions.
- Existing Gold API/XAUS spot tests, V42.4 logic, manual scan, Telegram, and market-data engine remain unchanged.
