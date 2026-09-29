# V43.6 — Targeted Funnel Fix

Built from V43.5 diagnostics. This release targets the measured bottlenecks without loosening TRIGGERED confirmation.

- Engine-aware touch/freshness handling: interaction-based structures (break/retest, reclaim/sweep, S&R switch) may survive up to 3 interactions; freshness-sensitive zones remain capped at 1.
- Distance no longer hard-rejects an otherwise valid WATCH. BACKGROUND/MAPPED locations can be saved for early monitoring; proximity still controls wake/ARMED behavior.
- Invalidation diagnostics preserve the specific lifecycle reason instead of collapsing all map failures into a generic INVALIDATED bucket.
- Every authorized `/api/alerts/tick` records a heartbeat, including no-WATCH cycles.
- V43.5 discovery diagnostics remain enabled.
- ARMED/TRIGGERED confirmation logic is unchanged.
