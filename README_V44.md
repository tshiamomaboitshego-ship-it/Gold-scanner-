# V44.0 Simple Core

Architecture: DATA -> DETECT & SHOW -> MONITOR -> ARMED -> TRIGGERED.

Key change: a detected structural location is shown before proximity/direction/trade-quality filters. Passed/behind or very distant points can remain visible as information without becoming active WATCHes. WATCH/ARMED/TRIGGERED remain separate states, and TRIGGERED still requires the existing closed-M1 confirmation. Diagnostics remain enabled.
