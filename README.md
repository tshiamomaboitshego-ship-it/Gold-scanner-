# Gold Scanner V34.4 — M1 Pullback State + Always-On M1

V34.4 is a targeted update to V34.2.

- M5 remains the major-zone generator.
- H1/M15/M5 remain weighted market context, but no longer hard-lock M1 point generation.
- M1 always searches both BUY and SELL precision structures.
- M1 points aligned with higher-timeframe context use normal qualification.
- Counter-context M1 points are classified as TRANSITION points and require stronger M1 structure/evidence.
- Fresh-only M1 memory remains: tested points and substantially overlapping rediscoveries stay hidden.
- M5 balanced/fresh-only behavior is unchanged from V34.2.
- No point is forced when no fresh structure qualifies.

Precision/evidence scores are not win probabilities. Zones are watch areas, not automatic entries.


V34.4 targeted fix: M1 pullback STATE detection is independent from M1 precision-point qualification. A meaningful recent M1 impulse plus opposite retracement can display PULLBACK_STARTING / PULLBACK_IN_PROGRESS without inventing a zone. Precision points still require fresh qualified structure, and used/overlapping M1 zones remain hidden.
