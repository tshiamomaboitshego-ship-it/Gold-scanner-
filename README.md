# Gold Scanner V33 — M1 Precision Layer

V33 keeps the V32 H1/M15/M5 scanner, fresh-zone filtering, persistent pullback tracking, Transition Engine, Reaction/Confirmation Engine, context/caching and forward-test behavior.

New: M1 Precision Layer. M1 is fetched with a short cache and is allowed to surface micro continuation watch areas only when M5 direction/transition is already established. M1 never replaces M5, never overrides H1/M15/M5, and never creates the primary direction by itself.

Render: `pip install -r requirements.txt` then `gunicorn server:app`.
