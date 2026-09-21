# Gold Scanner V39.3 — M1 Sequence + State + Trap Precision Quant Engine

Built from V39.2 without removing the M1 Pullback Bridge, mathematical precision or forward Quant Engine.

## Added in V39.3
- **M1 Price-Action Sequence Engine**: closed-M1 sweep/rejection-reclaim → displacement → micro structure break → follow-through stages. It is reaction evidence only and never manufactures a zone.
- **M1 Setup-State Machine**: CANDIDATE_FOUND → APPROACHING → TESTING → REJECTING → CONFIRMING → STRUCTURE_CONFIRMED, with failure/transition state when appropriate.
- **Failed-Setup / Trap Detection**: detects closed-candle acceptance through a candidate, failed reclaim plus opposite displacement, and flags a possible opposite transition.

M1 remains the primary setup/precision engine. M5/M15/H1 remain non-blocking context/confluence. Existing Pullback Bridge, mathematical clustering, micro-zone refinement, liquidity path/obstacle analysis, freshness/consumption and Quant tracking remain active.

These states are analysis/forward-testing aids, not automatic entries or guarantees.

## V39.4 additions
- State integrity: acceptance-through invalidation cannot be overwritten by later PA confirmation; reclaim after invalidation is a separate state.
- Persistent M1 state memory: phone localStorage keeps lifecycle history across scans and prevents silent state resets.
- M1 Compression/Expansion Engine: closed-candle range contraction, overlap and expansion context.
- M1 Market Regime 2.0: TRENDING / ORDERLY_TREND_OR_PULLBACK / COMPRESSION / EXPANSION_VOLATILITY_SHOCK / RANGE_OR_TRANSITION.
- Setup Similarity Quant: compares the latest frozen precision setup with the nearest categorical cohort; remains INSUFFICIENT until sample size develops.
All five are context/state/statistics layers. They do not invent zones or turn Quant statistics into probabilities.

## V39.5 additions — Candidate Ladder + Diagnostics
- **Pullback Candidate Ladder:** native M1 structure + Pullback Bridge candidates are ranked together as shallow/intermediate/deep areas.
- **WATCH vs QUALIFIED:** legitimate near-qualified structure remains visible as WATCH instead of disappearing; WATCH is not an entry signal.
- **Independent Break & Retest route:** closed-M1 break of a recent micro extreme can create a fresh first-retest candidate without requiring a classic continuation pullback.
- **Independent Transition route:** liquidity sweep + reclaim + opposite displacement can create a transition/reversal retest candidate.
- **Candidate Diagnostics:** shows raw → fresh → distance-valid → ranked → WATCH → QUALIFIED counts plus rejection reasons and route counts.
- The normal M1 structural qualification reference remains 66; this is not a blanket threshold reduction.
- M5/M15/H1 remain non-blocking context. Gemini/screenshots are not required for normal scans.
