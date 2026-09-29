# V44.4 — Proximity-Gated Early Locations

Keeps V44.3 early-location intelligence and V44.2 duplicate suppression.

Telegram EARLY alerts now require the location to be around current price action:
- price is already in the zone, OR
- EARLY_AHEAD + ACTIVE/APPROACHING + <= 3.0 M1 ATR away + <= $10 absolute distance.

Far valid locations remain visible/internal as BACKGROUND_TOO_FAR and are NOT put in sent history. If price later approaches them, they can alert once.

Duplicate alerts remain suppressed for sent locations.
