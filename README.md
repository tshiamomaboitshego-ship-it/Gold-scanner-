# Gold Scanner V30.3 — Dynamic Pullback Test Build

Adds a deterministic dynamic pullback engine to V30.1 while preserving fresh-only candidates.

- Detects a meaningful M5 impulse followed by an opposing retracement.
- Shows PULLBACK IN PROGRESS even when no fresh continuation zone qualifies.
- Searches for a fresh first retest of structure broken by the impulse (broken support for bearish continuation; broken resistance for bullish continuation).
- Never recycles a level already retested after the break.
- Existing H1/M15/M5, macro/session, caching, stale-feed protection, fresh-zone filtering, Pullback Continuation, New Move Origin, and forward-test logic remain.
- Dynamic pullback state is analysis, not an automatic trade instruction.
