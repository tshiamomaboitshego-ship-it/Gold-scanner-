# Gold Scanner V23 — Candidate Ranking + Zone Strength Engine

V23 is built from V22 after the 4308–4313 live test showed an important weakness: a technically meaningful M5 area can react briefly yet still be too high/too weak to be the strongest demand area.

## V23 upgrades
- Multi-candidate BUY/SELL zone ranking instead of stopping at the first plausible level.
- Deeper-zone awareness using deterministic FVG, order-block and swing candidates.
- Repeated-touch degradation and a zone consumption score.
- Body-penetration/acceptance penalties.
- Separate current reaction quality from historical zone quality.
- Failed-reaction/retest state so a temporary bounce is not treated as confirmation.
- Approach-aware lifecycle logic: old candles from before a zone approach no longer falsely invalidate a newly mapped zone.
- Candidate map is visible in the scan output for transparency.
- Existing V22 lifecycle/timing, V21 confluence, V20 Testing Lab, V19 shock protection and M5/M15/H1 OHLC architecture remain.

Important: zones are analysis locations, not guaranteed reversals or automatic entries. Demo-test and compare many outcomes before judging performance.
