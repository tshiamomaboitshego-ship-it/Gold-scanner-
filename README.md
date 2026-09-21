# Gold Scanner V39.2 — M1 Pullback Bridge + Precision Quant Engine

V39.2 is a targeted fix on top of V39.1. M1 remains the primary setup and precision timeframe; M5/M15/H1 remain non-blocking context/confluence.

## Targeted change
When the M1 pullback detector identifies a GOOD/STRONG active continuation pullback, V39.2 re-scans the active M1 impulse/retracement for structural candidates that the generic zone pool can miss:
- fresh M1 FVG / imbalance areas created by the impulse
- last-opposite-candle displacement origins
- broken micro support/resistance first-retest areas

These bridge candidates are not automatic signals. They still pass V39 mathematical clustering, micro-zone refinement, freshness/consumption checks, distance checks, liquidity/path analysis, redundancy control, candidate competition and the same M1 qualification floor. The UI marks bridge-derived candidates as PULLBACK BRIDGE.

## Preserved
- M1-first architecture
- M5/M15/H1 non-blocking context/confluence
- mathematical clustering and pullback geometry
- micro-zone refinement
- liquidity target/path and obstacle analysis
- evidence redundancy control
- forward-only Quant Engine
- VWAP/AVWAP remain optional external context when server-side volume is unavailable
