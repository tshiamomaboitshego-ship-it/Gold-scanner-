# V43.7 — Visible Points + Lifecycle Cleanup

Targeted follow-up to V43.6 diagnostics.

- Raw detector locations are now preserved in diagnostics so the user can verify that point detection is running even when no WATCH is accepted. These are diagnostic potential locations, not trade signals.
- Repeated touches now degrade quality rather than automatically deleting every fresh-zone candidate; heavily consumed structures are still rejected.
- WATCH saver no longer runs a second contradictory freshness gate after candidate generation/mapping already made that decision.
- A genuine RECLAIM_AFTER_INVALIDATION keeps the original structure dead but can be represented as a new reclaim setup lifecycle.
- Final WATCH decisions are logged with accepted/rejected/merged reason.
- Diagnostics display timestamps in South African Standard Time (Africa/Johannesburg, UTC+2).
- ARMED/TRIGGERED confirmation logic remains strict and unchanged.
