# Gold Scanner V26.2 — Dual Opportunity Engine

V26.2 keeps the V26.1 reference-price sync and makes PULLBACK CONTINUATION and NEW MOVE ORIGIN independent candidate families.

Changes:
- Adds recent/local M5 swing and local-range origin candidates near price.
- Current price ranks relevance only after structural candidates are generated.
- Pullback continuation and new-move-origin receive separate scores.
- New-move-origin score exposes liquidity/location, structure transition, displacement, freshness, and HTF-context components.
- Distance influence is reduced so a farther continuation target does not automatically hide a strong nearby origin.
- Existing H1/M15/M5 OHLC, lifecycle, Gemini visual cross-check, quota-safe data-only mode, testing lab, and V26.1 price-sync behavior remain.

Important: zones are watch areas, not predictions or automatic entries. Validate with forward/demo testing.
