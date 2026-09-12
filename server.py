import os
import json
import base64

from flask import Flask, request, jsonify, send_from_directory
from google import genai
from google.genai import types

app = Flask(__name__, static_folder=".", static_url_path="")

SYSTEM = """You are Gold Scanner V1, a conservative XAUUSD chart-analysis assistant.
The user supplies three screenshots of the SAME market context:
- H1: determine higher-timeframe direction and major structure.
- M15: determine setup, support/resistance, consolidation, breakout/retest context.
- M5: determine entry confirmation or lack of confirmation.

Return BUY, SELL, or WAIT. WAIT is preferred when evidence conflicts, price is ranging/choppy,
screenshots are unclear, market is closed, or a clean entry is absent.

Do not claim a win probability. "confidence_score" is only confidence in the chart interpretation,
from 0 to 100.

Use visible prices only; never invent precision that cannot be read from the screenshot.
If an entry is not justified, use null for entry/SL/TP and explain why.
For BUY/SELL, propose a conservative entry zone, stop loss, TP1, TP2, and approximate
risk/reward based on visible structure.

Return ONLY valid JSON matching this exact shape:
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
  "reasons": ["...", "..."]
}
"""

def data_url_to_part(data_url: str):
    header, encoded = data_url.split(",", 1)
    mime_type = header.split(";", 1)[0].replace("data:", "")
    image_bytes = base64.b64decode(encoded)
    return types.Part.from_bytes(data=image_bytes, mime_type=mime_type)

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
def analyze():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "Server is missing GEMINI_API_KEY.", 500

    data = request.get_json(force=True)

    for key in ("h1", "m15", "m5"):
        if key not in data or not str(data[key]).startswith("data:image/"):
            return f"Missing or invalid {key} screenshot.", 400

    try:
        client = genai.Client(api_key=api_key)

        contents = [
            (
                SYSTEM
                + "\n\nAnalyze these XAUUSD screenshots in this order: H1, M15, M5. "
                  "Return only the requested JSON."
            ),
            data_url_to_part(data["h1"]),
            data_url_to_part(data["m15"]),
            data_url_to_part(data["m5"]),
        ]

        response = client.models.generate_content(
            model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )

        text = (response.text or "").strip()

        if not text:
            return jsonify({"error": "Gemini returned an empty response."}), 502

        result = json.loads(text)
        return jsonify(result)

    except json.JSONDecodeError:
        return jsonify({
            "error": "Gemini returned invalid JSON.",
            "raw": text if "text" in locals() else ""
        }), 502
    except Exception as exc:
        return jsonify({"error": f"Analysis failed: {str(exc)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
