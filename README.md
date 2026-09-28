# Gold Scanner V41.4 — Automatic Opportunity Alerts

Built directly on V41.3. Manual Scan remains available.

## New in V41.4
- Telegram phone alerts without storing the bot token in source.
- Server-side automatic opportunity lifecycle state for A/A+ opportunities.
- Alerts on LOCKED, ARMED, TRIGGERED, TP1, TP2, STOPPED/INVALIDATED, EXPIRED/MISSED.
- Duplicate-alert suppression.
- `/api/alerts/test` test notification endpoint.
- `/api/alerts/status` status endpoint.
- `/api/alerts/tick` scheduler-friendly monitor endpoint.
- Optional built-in background monitor.

## Required environment variable
`TELEGRAM_BOT_TOKEN` = the private token from BotFather. Never put it in source or share it.

The configured default chat id is `6747412656`. You can override it with:
`TELEGRAM_CHAT_ID=...`

## Automatic monitor
Set:
`AUTO_MONITOR_ENABLED=true`
`AUTO_MONITOR_SECONDS=300`

A sleeping/free host cannot wake itself. For a host that sleeps, keep `AUTO_MONITOR_ENABLED=false` and call `POST /api/alerts/tick` from a reliable external scheduler. Optionally protect it with `MONITOR_TICK_SECRET` and send that value in the `X-Monitor-Secret` header.

Monitor frequency consumes market-data API quota. Choose the interval to fit your data-provider limits. Manual Scan continues to work regardless of automatic monitoring.

## Important
Grades rank evidence, not win probability. Notifications are decision-support alerts, not guaranteed profitable signals and do not execute trades.

## V41.4 stale-trigger protection (2026-09-28)
Automatic TRIGGERED alerts now perform a final current-price freshness check immediately before Telegram delivery. If price has already crossed structural invalidation, the alert becomes INVALIDATED. If price has moved back through the entry zone or has already travelled too far toward TP1, the alert becomes MISSED — DON'T CHASE. Trigger alerts also include current Gold price, provider M1 detection time, and the UTC freshness-check time.

The default maximum favorable progress before a trigger is considered missed is 15% of the distance from the entry-zone edge to TP1. It can be changed with the optional Render environment variable `V414_TRIGGER_MAX_PROGRESS` (accepted range 0.05–0.50). This is a stale-alert guard, not a profitability estimate.

## V41.4 reliability hardening (2026-09-28)
Automatic alerts now add a final execution-reliability gate: unique opportunity IDs, strict M1 trigger-age validation, stale-feed blocking, tighter favorable-move/chase protection, adverse zone-departure rejection, structural invalidation priority, and trigger/freshness timestamps in Telegram. A stale or delayed trigger is closed as MISSED/DATA STALE instead of being reused. One active locked opportunity remains authoritative until terminal lifecycle state.

Optional Render overrides: `V414_TRIGGER_MAX_AGE_SECONDS` (default 45 seconds after the trigger M1 candle closes), `V414_TRIGGER_MAX_PROGRESS` (default 0.10 of zone-to-TP1 distance), and `V414_MAX_M1_FEED_AGE_MINUTES` (default 2.0).

## V41.4 reliability/quality-control patch
- Automatic ON/OFF control added to the phone UI. OFF makes scheduled `/api/alerts/tick` calls return without scanning or Telegram alerts; Manual Scan still works. Turning ON clears old lifecycle state and starts fresh.
- The switch is protected by the same `MONITOR_TICK_SECRET`; the phone asks once and stores it in local browser storage.
- Strict lifecycle ordering: TP1/TP2 and STOPPED are only possible after the exact opportunity has an accepted TRIGGERED state. An untriggered setup crossing invalidation is INVALIDATED, not a losing trade.
- New-lock discovery freshness guard rejects automatic alerts when live price shows the move has already materially progressed or traded adversely through the proposed entry before discovery.
- Existing trigger-age, market-data freshness, structural invalidation and don't-chase guards remain active.

## V41.5 Passive Observability upgrade

V41.5 deliberately leaves the V41.4 signal/entry decision logic unchanged. It adds a best-effort rolling JSONL performance/diagnostic logger and a passive market-regime label so forward testing can explain why the scanner was quiet or why a candidate was rejected.

Recorded fields include scan time, provider M1 time/feed age, current price, regime, precision state, candidate counts/diagnostics, hybrid state/decision, best-point summary, discovery rejection, opportunity ID and lifecycle event. DATA_WAIT and AUTO_OFF are also recorded.

Diagnostics endpoint: `GET /api/diagnostics/v415?limit=100` protected by the same `MONITOR_TICK_SECRET` when configured. This is observational only: it does not change grades, candidate selection, freshness, SL/TP, or Telegram lifecycle decisions.

On Render's free filesystem the JSONL file is ephemeral and can be lost on restart/redeploy. This version is for forward-test diagnostics; persistent database storage can be added later if needed.
