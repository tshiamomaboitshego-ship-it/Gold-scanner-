# V43.4 Hybrid Watch Fix

- Removed the old active-continuation-pullback gate from the generic M1 structural candidate pool.
- Pullback-specific routes still require a genuine continuation pullback.
- Early location mapping now also receives independent Break+Retest, Liquidity Sweep+Reclaim, and Compression Break candidates.
- WATCH admission now accepts legitimate WATCH-grade candidates; ARMED/TRIGGERED confirmation remains strict.
- APPROACHING watch radius broadened from 2.0 to 3.0 M1 ATR.
- Added last_watch_funnel diagnostics to monitor candidate rejection/saving.
- Existing multi-watch, automation, Telegram, AUTO ON/OFF, freshness, invalidation, risk and lifecycle protections are retained.
