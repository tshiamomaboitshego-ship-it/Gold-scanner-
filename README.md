# Gold Scanner V34.6 — Inducement Context

Built from V34.4. Keeps balanced fresh-only M5 zones, always-on M1 precision, M1 pullback-state detection, transition/reaction engines, caching and context layers.

V34.6 adds a conservative inducement relationship layer. Minor internal liquidity sitting sensibly in front of an existing BUY/SELL candidate can add a small +4 evidence/ranking bonus. Inducement never creates a zone, never forces direction, never vetoes a valid zone, and is not mandatory. This avoids re-tightening the scanner while improving candidate ranking/selection.

Evidence scores are not win probabilities. Zones are watch areas, not automatic entries.


## V34.6 Sequence Intelligence
Adds five supporting concepts without making them mandatory gates: Market Structure Shift (MSS), liquidity void / Balanced Price Range (BPR), failed-auction acceptance vs rejection, nested macro/micro dealing ranges, and draw-on-liquidity path context. These can add small relationship/ranking bonuses to existing fresh M5/M1 candidates; they never create a point by themselves and never veto an otherwise qualified point.
