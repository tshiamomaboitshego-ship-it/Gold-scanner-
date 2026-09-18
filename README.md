# Gold Scanner V34.2 — Balanced Fresh Points

Targeted rebalance built from V34.1. Fresh-only behavior is preserved.

Changes:
- M5/M1 structural candidate pool widened before freshness filtering, preventing used high-ranked zones from crowding out valid fresh zones.
- Fresh/untested rules remain intact; used/retested zones are still hidden.
- M5 dynamic pullback and order-block detection are modestly less restrictive, while first-retest logic remains.
- M1 directional gate and final evidence threshold are modestly rebalanced; core M1 structure and freshness are still required.
- No forced BUY/SELL point. If nothing qualifies, scanner still reports no fresh qualified area.
- Existing transition, reaction, persistent tracking, macro/session context, API caching and forward-test features are retained.

Evidence/precision scores are not win probabilities and zones are analysis/watch areas, not automatic entries.
