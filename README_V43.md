# V43 Simplified Hybrid Scanner

V43 is a simplification pass, not a new strategy.

- Data: XAUS diagnostics/reference + Twelve Data M1 OHLC; higher timeframes derived locally where supported.
- Opportunity routes retained: Pullback, Break + Retest, Sweep + Reclaim, Consolidation/Compression Break.
- Visible lifecycle: WATCH -> ARMED -> TRIGGERED.
- Internal LOCKED state is preserved only to stop an active opportunity being silently replaced across scans; the phone UI labels it WATCH.
- WATCH and ARMED are not entries. TRIGGERED still requires closed-M1 confirmation.
- Existing invalidation, structural risk plan, freshness/used-zone suppression, logging and diagnostics remain available.
- No new indicator or strategy was added.
