# Gold Scanner V42 — Early Location Intelligence

V42 changes the scanner architecture from late discovery toward **MAP → LOCK → WAIT → REACT → CONFIRM → TRIGGER**.

## What changed
- Maps ranked M1 structural locations while they are still ahead of live price.
- A mapped location is **not an entry**. A/A+ location evidence may be locked early, then the existing lifecycle waits for price interaction and closed-M1 reaction/confirmation.
- Existing V41.5 lifecycle, structural SL/TP, stale-trigger guard, Telegram, automatic ON/OFF control, caching/rate-limit protections and observability are retained.
- Adds a visible V42 Early Location Map to the phone UI.
- Adds a visible Live Scanner Diagnostics panel with a refresh button. It shows feed age, regime, candidate funnel, rejection reasons, mapped-ahead count and current lifecycle state.
- Manual live scans also show the V42 early map.

## Important
Evidence grades rank rule-based evidence; they are not probabilities or guarantees. LOCKED means a location is being watched, not that a trade should be entered. TRIGGERED remains the scanner's entry-qualified lifecycle event.

## Deploy
Use the same Render service and environment variables as V41.5. Keep `TELEGRAM_BOT_TOKEN` private. Keep the same `MONITOR_TICK_SECRET` and cron POST endpoint `/api/alerts/tick`. No new paid API is required.

## Diagnostics
On the scanner page tap **REFRESH LIVE DIAGNOSTICS**. The browser asks for the existing Monitor Secret if it is not already stored locally. Do not share that secret.


## V42.3 Context Intelligence Suite
Adds seven coordinated intelligence layers: proximity, passive market regime, price path, location strength, reaction, liquidity/obstacle, and failure intelligence. These layers rank/map/monitor opportunities; they do not turn weak locations into trades. Final TRIGGERED confirmation remains strict and closed-M1 based.
