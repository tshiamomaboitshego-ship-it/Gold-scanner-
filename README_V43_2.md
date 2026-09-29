# V43.2 Automatic Hybrid
- Cron endpoint remains POST /api/alerts/tick.
- Every cron tick uses XAUS for lightweight monitoring of all saved WATCHes.
- About every 5 minutes (V432_DISCOVERY_SECONDS, default 300), it performs one automatic OHLC discovery scan.
- New distinct WATCHes are merged with existing active WATCHes, up to the configured watch limit.
- Telegram notifies NEW WATCH and later ARMED/TRIGGERED/terminal lifecycle changes.
- Manual SCAN MARKET remains available as an immediate discovery override.
- WATCH/ARMED are not entries; TRIGGERED still requires the existing confirmation logic.
