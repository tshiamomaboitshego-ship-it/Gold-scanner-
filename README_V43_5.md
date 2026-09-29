# V43.5 — Full Discovery & Automation Diagnostics

This build does not loosen TRIGGERED or add a new trading strategy. It makes the automatic scanner observable.

Adds:
- automation health: AUTO, cron/tick, discovery time/result, XAUS status, Telegram configuration, active WATCH count
- last discovery funnel: raw -> fresh -> ranked -> candidate WATCH -> qualified -> mapped -> saved WATCH
- exact rejection counters from candidate, early-map, and WATCH-saver stages
- detected/ranked candidate points shown as diagnostics even when they do not become a WATCH
- rolling discovery history (up to 288 cycles in scanner state) and accumulated rejection counts
- `/api/diagnostics/v435` protected by the existing Monitor Secret

The four setup families, multi-WATCH lifecycle, AUTO ON/OFF, cron endpoint, Telegram alerts, freshness checks, and strict ARMED/TRIGGERED confirmation remain intact.

Diagnostic points are not trade signals.
