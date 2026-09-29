# V44.3 — Early Location Intelligence

Adds upstream location detection without weakening entry confirmation.

New early-location sources:
- confirmed swing supply/demand and broken S/R retest structures already present in M1 metrics
- fresh/mitigated impulse-origin supply/demand blocks
- previous-day and active-session highs/lows

Flow remains:
DATA → DETECT/SHOW → EARLY POINT (once) → MONITOR → PRICE AT POINT → STRICT CONFIRMATION → outcome.

Important: early locations are not trade entries or probability claims. V44.2 24-hour fuzzy duplicate suppression remains active so the same overlapping point is not repeatedly sent.
