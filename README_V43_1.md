# V43.1 Smart Multi-Watch

- Manual SCAN MARKET is the discovery step.
- Saves up to 5 distinct nearby B/A/A+ WATCH opportunities from the existing four setup routes.
- Overlapping same-side locations are merged by keeping the higher-ranked representative.
- `/api/alerts/tick` is re-enabled for an external scheduler/cron and protected by `MONITOR_TICK_SECRET` when configured.
- Each tick first checks keyless XAUS spot against ALL saved WATCH points.
- If no WATCH is near, no Twelve Data OHLC scan is requested.
- If one or more WATCH points are near, one shared OHLC scan updates all nearby lifecycles.
- Telegram alerts only on meaningful lifecycle changes: ARMED, TRIGGERED, TP1/TP2, invalidation/expiry/missed/stop.
- WATCH/ARMED are not entries; TRIGGERED still requires the existing closed-M1 confirmation and freshness gates.
