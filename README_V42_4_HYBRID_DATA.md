# V42.4 R0 Hybrid Data Architecture

- XAUS spot: primary current/reference price for proximity.
- XAUS intraday: sampled ~2-minute price-path context only. Never treated as OHLC.
- Twelve Data: one XAU/USD 1-minute OHLC request when the shared M1 cache needs refresh.
- M5/M15/H1: derived locally from the shared M1 OHLC store.
- Gold API test endpoints remain diagnostic/backup only.
- Cron/automatic polling remains outside this manual-scan architecture.
- Freshness protection remains active; stale M1/M5 data cannot qualify as fresh execution data.
- Fixed scan freshness check so locally derived M5 can be accepted when the shared M1 feed is fresh.

The scan response exposes `price_meta.data_sources` and `price_meta.xaus_intraday` so the source of each data layer is visible.
