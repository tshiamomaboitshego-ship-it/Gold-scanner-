# Gold Scanner V30.1 Fresh-Zone Test Build

Targeted update to V30. No new market concepts were added.

## What changed
- Main BUY/SELL candidate lists now surface only fresh, ahead-of-price zones.
- Zones with repeated interaction, an already-detected rejection/follow-through, or meaningful consumption are hidden as NEW opportunities.
- Hidden used zones remain inside the market engine as historical structure/context; they are not deleted from analysis.
- Fresh zones saved by an earlier scan continue to be graded separately after price reaches them.
- Forward-test lifecycle can report TESTED, REACTED, FOLLOW_THROUGH, or INVALIDATED.
- If nothing fresh qualifies, UI says NO FRESH QUALIFIED AREA.

## Unchanged
H1/M15/M5 structure, Pullback Continuation, New Move Origin, BOS/CHoCH, FVG/OB/liquidity logic, session/day/week intelligence, volatility regime, USD/FRED/CFTC context, API caching and stale-feed protection remain intact.

This is an analysis/testing tool, not an automatic trade instruction or guarantee.
