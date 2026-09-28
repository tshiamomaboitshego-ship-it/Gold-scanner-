# Gold Scanner V42.4 — R0 Market Data Engine

This build preserves V42.3 trading/context intelligence and changes the free-data plumbing.

- One shared primary M1 Twelve Data request instead of independent M1/M5/M15/H1 requests.
- M5, M15 and H1 are resampled locally from closed M1 candles.
- Current reference price reuses the shared M1 store; `/price` is no longer polled by the scanner path.
- Shared cache is persisted in the existing market-data cache file and reused by cron/manual scans.
- Provider cooldown is respected. If there is no cache yet, scanner returns DATA WAIT rather than fabricating a signal.
- Stale M1 still blocks fresh trigger eligibility.
- Diagnostics expose `data_engine`, derived timeframes, primary-store bars, and provider requests for the scan.

Default M1 history request: 3000 one-minute bars (configurable with M1_PRIMARY_OUTPUTSIZE, bounded 1800–5000).
