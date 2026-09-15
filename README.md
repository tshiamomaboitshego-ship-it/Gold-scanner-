# Gold Scanner V9.2 — M5 Backend Fix

V9.2 fixes the remaining backend code that was still requiring H1 + M15 + M5.

The complete scan path is now M5-only:
M5 screenshot → one Gemini request → BUY SETUP / SELL SETUP / NO TRADE → fresh entry zone + invalidation + TP1/TP2/TP3.

No H1 or M15 image is required or sent to Gemini.
