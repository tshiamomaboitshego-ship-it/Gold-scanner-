# Gold Scanner V39.3 — M1 Sequence + State + Trap Precision Quant Engine

Built from V39.2 without removing the M1 Pullback Bridge, mathematical precision or forward Quant Engine.

## Added in V39.3
- **M1 Price-Action Sequence Engine**: closed-M1 sweep/rejection-reclaim → displacement → micro structure break → follow-through stages. It is reaction evidence only and never manufactures a zone.
- **M1 Setup-State Machine**: CANDIDATE_FOUND → APPROACHING → TESTING → REJECTING → CONFIRMING → STRUCTURE_CONFIRMED, with failure/transition state when appropriate.
- **Failed-Setup / Trap Detection**: detects closed-candle acceptance through a candidate, failed reclaim plus opposite displacement, and flags a possible opposite transition.

M1 remains the primary setup/precision engine. M5/M15/H1 remain non-blocking context/confluence. Existing Pullback Bridge, mathematical clustering, micro-zone refinement, liquidity path/obstacle analysis, freshness/consumption and Quant tracking remain active.

These states are analysis/forward-testing aids, not automatic entries or guarantees.
