# V44.1 — Early Point Alerts

Core flow: DATA → DETECT + SHOW + ALERT EARLY → PRICE AT POINT → CONFIRMED / FAILED.

- Telegram alerts newly detected credible mapped locations before WATCH admission.
- WATCH remains internal monitoring state to avoid duplicate notification delay/spam.
- Discovery default reduced from 5 minutes to 3 minutes (configurable with V432_DISCOVERY_SECONDS; minimum 120s).
- Each early point records detected time, detected Gold price, and timing classification.
- Points already passed when first discovered are visible in diagnostics but are not sent as fresh Telegram alerts.
- ARMED notification text now means PRICE AT EARLY POINT.
- Strict closed-M1 confirmation/trigger logic is retained.
- Early point alerts are decision support, not entry instructions.
