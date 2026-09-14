import os
import json
import base64

from flask import Flask, request, jsonify, send_from_directory
from google import genai
from google.genai import types

app = Flask(__name__, static_folder=".", static_url_path="")

FULL_SYSTEM = '''You are Gold Scanner V2, a conservative XAUUSD chart-analysis assistant.
The user supplies three screenshots of the SAME market context:
- H1: determine higher-timeframe direction and major structure.
- M15: determine setup, support/resistance, consolidation, breakout/retest context.
- M5: determine entry confirmation or lack of confirmation.

Return BUY, SELL, or WAIT. WAIT is preferred when evidence conflicts, price is ranging/choppy,
screenshots are unclear, market is closed, or a clean entry is absent.

Do not claim a win probability. "confidence_score" is confidence in the chart interpretation only.
Use visible prices only; never invent precision that cannot be read from the screenshot.
If an entry is not justified, use null for entry/SL/TP.

When returning WAIT, include a specific "rescan_condition" that tells the user what price action
or level would justify taking fresh screenshots and scanning again.

Return ONLY valid JSON matching:
{
  "signal": "BUY|SELL|WAIT",
  "confidence_score": 0,
  "trend": "Bullish|Bearish|Neutral/Mixed",
  "market_state": "Trending|Pullback|Range|Breakout|Reversal watch|Unclear|Market closed",
  "entry_zone": null,
  "stop_loss": null,
  "tp1": null,
  "tp2": null,
  "risk_reward": null,
  "rescan_condition": "...",
  "reasons": ["...", "..."]
}
'''

QUICK_SYSTEM = '''You are Gold Scanner V2 Quick Scan, a conservative XAUUSD screenshot scanner.
You receive ONE chart screenshot and its timeframe (usually M5).

Your job is to make a fast preliminary decision: BUY, SELL, or WAIT using only what is visible.
Because there is no higher-timeframe confirmation, be more conservative than a full multi-timeframe scan.

Rules:
- Never pretend you can see H1/M15 if they were not supplied.
- Prefer WAIT if the screenshot is unclear, price is ranging, price is already extended after a breakout,
  price is sitting directly at major visible support/resistance, or confirmation is weak.
- For BUY/SELL, require visible structure plus a clear trigger/retest/rejection on the supplied timeframe.
- Do not claim a win probability. "confidence_score" is confidence in the chart interpretation only.
- Use visible prices only. Do not invent exact prices you cannot read.
- If WAIT, give a specific "rescan_condition" telling the user what visible price action or level should
  trigger another Quick Scan.
- If BUY/SELL, include an entry zone, stop loss, TP1, TP2, and approximate risk/reward.
- Mention in reasons that this is a single-timeframe quick scan when relevant.

Return ONLY valid JSON matching:
{
  "signal": "BUY|SELL|WAIT",
  "confidence_score": 0,
  "trend": "Bullish|Bearish|Neutral/Mixed",
  "market_state": "Trending|Pullback|Range|Breakout|Reversal watch|Unclear|Market closed",
  "entry_zone": null,
  "stop_loss": null,
  "tp1": null,
  "tp2": null,
  "risk_reward": null,
  "rescan_condition": "...",
  "reasons": ["...", "..."]
}
'''

def data_url_to_part(data_url: str):
    header, encoded = data_url.split(",", 1)
    mime_type = header.split(";", 1)[0].replace("data:", "")
    image_bytes = base64.b64decode(encoded)
    return types.Part.from_bytes(data=image_bytes, mime_type=mime_type)

def run_gemini(contents):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None, ("Server is missing GEMINI_API_KEY.", 500)

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=os.environ.get("GEMINI_MODEL", "gemini-3.6-flash"),
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.15,
        ),
    )
    text = (response.text or "").strip()
    if not text:
        return None, ("Gemini returned an empty response.", 502)
    try:
        return json.loads(text), None
    except json.JSONDecodeError:
        return None, (f"Gemini returned invalid JSON: {text[:500]}", 502)

@app.get("/")
def home():
    return send_from_directory(".", "index.html")

@app.get("/manifest.json")
def manifest():
    return send_from_directory(".", "manifest.json")

@app.get("/sw.js")
def sw():
    return send_from_directory(".", "sw.js")

@app.get("/icon.svg")
def icon():
    return send_from_directory(".", "icon.svg")

@app.post("/api/analyze")
def analyze_full():
    data = request.get_json(force=True)
    for key in ("h1", "m15", "m5"):
        if key not in data or not str(data[key]).startswith("data:image/"):
            return jsonify({"error": f"Missing or invalid {key} screenshot."}), 400

    try:
        contents = [
            FULL_SYSTEM + "\nAnalyze these XAUUSD screenshots in this order: H1, M15, M5.",
            data_url_to_part(data["h1"]),
            data_url_to_part(data["m15"]),
            data_url_to_part(data["m5"]),
        ]
        result, error = run_gemini(contents)
        if error:
            return jsonify({"error": error[0]}), error[1]
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": f"Analysis failed: {str(exc)}"}), 500

@app.post("/api/quick-analyze")
def analyze_quick():
    data = request.get_json(force=True)
    image = data.get("image")
    timeframe = str(data.get("timeframe", "M5")).upper()

    if not image or not str(image).startswith("data:image/"):
        return jsonify({"error": "Missing or invalid chart screenshot."}), 400

    if timeframe not in {"M1", "M5", "M15", "M30", "H1", "H4"}:
        timeframe = "M5"

    try:
        contents = [
            QUICK_SYSTEM + f"\nThe supplied XAUUSD screenshot timeframe is {timeframe}. Analyze it now.",
            data_url_to_part(image),
        ]
        result, error = run_gemini(contents)
        if error:
            return jsonify({"error": error[0]}), error[1]
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": f"Quick analysis failed: {str(exc)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
