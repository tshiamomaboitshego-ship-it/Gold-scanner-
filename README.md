# Gold Scanner V1

Phone-first XAUUSD screenshot scanner.

## What it does
Upload three screenshots of the same Gold market context:
- H1 = main direction
- M15 = structure/setup
- M5 = entry confirmation

The app returns BUY / SELL / WAIT plus:
- confidence score (chart interpretation only)
- trend
- market state
- entry zone
- stop loss
- TP1 / TP2
- risk/reward
- reasons

## Why it needs hosting
Your phone is the only device you need to USE it, but the AI image analysis runs on a cloud backend.
Do not put an API key inside the browser code or APK.

## Run/deploy
Required environment variable:
OPENAI_API_KEY=...

Optional:
OPENAI_MODEL=gpt-5

Install:
pip install -r requirements.txt

Run:
python server.py

Then open the hosted URL on Android. In Chrome, use "Add to Home screen" / "Install app" if offered.

## APK later
This PWA is the fastest safe V1. Once the scanner is tested, the same hosted app can be wrapped in an Android shell (for example Capacitor) and exported as an APK.
