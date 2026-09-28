# Gold Scanner V41.2 — Adaptive Entry + Opportunity Tracking

Built directly from V41.1 Multi-Setup Hybrid. V40.1 pullback intelligence and the V41.1 setup families remain intact.

## V41.2 changes
- Locks the selected best opportunity across later phone scans instead of silently replacing/disappearing it.
- Two-stage timing: LOCATION QUALITY first, then a compact closed-M1 FAST TRIGGER after price tests the locked point.
- Lifecycle: LOCKED → ARMED → TRIGGERED → TP1/TP2 or STOPPED/INVALIDATED.
- Existing structural SL, TP1 and TP2 travel with the locked setup.
- Pullback, Break+Retest, Sweep+Reclaim and Consolidation-Break discovery remain available.
- New candidates stay secondary while an active locked setup is alive.
- Existing forward-test/quant logging remains; scores are evidence rankings, not win probabilities.

## Fast trigger
After a high-quality point is selected and tested, V41.2 can trigger from compact closed-M1 evidence (reclaim plus directional close/follow-through, trap+candle, or directional restart evidence) rather than repeatedly requiring the entire original filter stack.

This is an experimental decision-support scanner. Triggered/qualified setups can still lose.
