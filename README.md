# Gold Lunar & Astrology Research Lab

A separate, phone-friendly research dashboard for XAUUSD. It does not generate BUY/SELL signals or place trades and does not modify the existing Gold Scanner / Telegram bot.

## Features
- Swiss Ephemeris Moshier calculations for current tropical geocentric planetary positions.
- Calculated new moon, first quarter, full moon and last quarter dates.
- Planetary aspects within a 3-degree orb.
- Exploratory historical daily XAUUSD return comparisons following lunar phase events, with cautious historical-bias labels when a minimum sample and simple consistency thresholds are met.
- Optional historical daily close chart.
- SAST (Africa/Johannesburg) display in the browser; astronomy events are calculated in UTC.

## Deploy as a separate Render web service
1. Upload this folder to a **new GitHub repository**. Do not replace the current gold-scanner repository.
2. In Render, create a new Web Service from the new repository.
3. Render should detect `render.yaml`, or configure build command `pip install -r requirements.txt` and start command `gunicorn app:app --workers 1 --threads 4 --timeout 120`.
4. Open the service URL on the phone. Use browser menu → Add to Home screen if desired.

## Data and limitations
- Astronomy: `pyswisseph` with the built-in Moshier ephemeris, so a separate ephemeris file is not needed.
- Historical gold: Yahoo Finance ticker `XAUUSD=X` via `yfinance`; availability, coverage, timestamps and prices are controlled by the provider and may be delayed or fail. The first history request can take a while.
- Phase-event return tests match the event to the next available daily close. This approximation can shift timing around weekends/holidays. The comparison is exploratory and is not a causal test or evidence of a tradable edge.
- No API keys, broker credentials, Telegram token, order placement, or automated trade execution are required.
- The dashboard is a standalone research tool; the existing V44.4 scanner/Telegram code is left unchanged.
