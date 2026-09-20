# Gold Scanner V35 — VWAP + True Order Flow Ready

Built directly from V34.6. The structural engine is preserved: fresh-only M5 zones, always-on M1 precision points, pullback-state separation, transition/reaction logic, inducement, MSS, BPR, failed-auction context, nested dealing ranges and liquidity-path context.

## V35 additions
- VWAP context is calculated only when the connected provider supplies real reported volume. It prefers configured Gold-futures data; it never invents spot-XAU volume.
- VWAP annotates existing points as location context only. It does not create, delete, move or veto a point.
- A true-order-flow layer is present for genuine bid/ask aggressor-volume data. OHLCV is deliberately **not** converted into fake order flow.
- Until a compatible true order-flow feed is connected, the UI says `WAITING FOR TRUE DATA`.
- Existing M1 points show their VWAP and order-flow context directly.

Twelve Data's VWAP documentation says its VWAP endpoint applies to all instruments except currencies, so V35 does not pretend XAU/USD has centralized exchange volume. `GOLD_FUTURES_SYMBOL` remains the optional futures symbol setting from the earlier scanner. Evidence scores are not win probabilities; zones are watch areas, not automatic entries.

## V36 Precision Context additions
- TPO / time-at-price Market Profile from closed M1 OHLC (POC, VAH, VAL, HVN/LVN). It is explicitly not Volume Profile and fabricates no volume.
- UTC session/opening-range + Initial Balance context (Asia, London, New York) from M1 price/time.
- Quantitative M1 acceptance/rejection after a zone is tested: penetration, closes inside/beyond, reclaim speed, displacement.
- TPO/session evidence is a small non-blocking ranking bonus only after the existing structural point qualifies. It cannot manufacture or veto a point.
- VWAP and true order flow remain optional/unavailable unless trustworthy volume/aggressor data is connected.

## V36.1 Phase 1 freeze additions
- Dedicated local Phase-1 logger for fresh M1 Precision points and their existing context. It does not change point generation, scoring, zones, or qualification.
- Data-quality guard records latest M1/M5 timestamps and ages. Stale execution-feed scans remain viewable but are excluded from Phase-1 logging/statistics.
- Phase-1 freshness thresholds: M1 <= 3 minutes, M5 <= 8 minutes.
