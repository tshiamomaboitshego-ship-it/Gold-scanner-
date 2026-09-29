# V44.2 — Deduped Early Alerts

- An EARLY POINT is notified once, then monitored silently.
- Rediscovery of the same side/setup in an overlapping or near-identical zone is suppressed, even if boundaries drift slightly.
- Sent point fingerprints persist for 24 hours (up to 500 records), including after a point later fails/completes, preventing immediate recreation spam.
- Meaningful lifecycle changes (PRICE AT POINT / TRIGGERED / INVALIDATED etc.) retain their existing one-event-per-state notification protection.
- Diagnostics mark rediscovered points as `SUPPRESSED_DUPLICATE`.
