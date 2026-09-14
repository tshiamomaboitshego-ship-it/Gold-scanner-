import os, json, base64
from flask import Flask, request, jsonify, send_from_directory
from google import genai
from google.genai import types

app = Flask(__name__, static_folder=".", static_url_path="")

SYSTEM = """You are Gold Scanner V3, a conservative XAUUSD screenshot-analysis assistant.
The user gives ONE current chart screenshot and states its timeframe.

Analyze only what is actually visible. Never pretend you can see other timeframes.
Use visible market structure, momentum, swing highs/lows, support/resistance,
breakout/retest behavior, rejection, consolidation, and current visible price.

Your goal is ONE clean actionable conclusion, not a list of conflicting levels.

Return BUY, SELL, or WAIT.
BUY/SELL requires a reasonably clear setup on the supplied chart.
Prefer WAIT when price is extended, ranging/choppy, at a major visible barrier,
the screenshot is unclear, the market is closed, or confirmation is insufficient.

For BUY/SELL:
- Give one practical entry zone based on visible price.
- Give stop loss.
- Give TP1 and TP2.
- Give approximate risk/reward.
- Give ONE short "trade_plan" sentence explaining what must happen for the entry to remain valid.
- "main_level_to_watch" should be the most important price/zone for this setup.

For WAIT:
- Do not fill the screen with many levels.
- Pick ONE best main level/zone to monitor.
- "rescan_condition" must clearly tell the user what should happen around that ONE level before taking a fresh screenshot.
- Entry/SL/TP/RR should be null.

confidence_score means confidence in the screenshot interpretation, NOT probability of winning.
Never claim guaranteed profit or a win probability.
Never invent price precision that is not readable.

Return ONLY valid JSON:
{
 "signal":"BUY|SELL|WAIT",
 "confidence_score":0,
 "timeframe":"M5",
 "trend":"Bullish|Bearish|Neutral/Mixed",
 "market_state":"Trending|Pullback|Range|Breakout|Reversal watch|Unclear|Market closed",
 "current_price":null,
 "main_level_to_watch":null,
 "entry_zone":null,
 "stop_loss":null,
 "tp1":null,
 "tp2":null,
 "risk_reward":null,
 "trade_plan":"",
 "rescan_condition":"",
 "reasons":["...","..."]
}"""

def image_part(data_url):
    header, encoded = data_url.split(",", 1)
    mime = header.split(";", 1)[0].replace("data:", "")
    return types.Part.from_bytes(data=base64.b64decode(encoded), mime_type=mime)

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

@app.post("/api/scan")
def scan():
    data = request.get_json(force=True)
    image = data.get("image")
    tf = str(data.get("timeframe","M5")).upper()
    if not image or not str(image).startswith("data:image/"):
        return jsonify({"error":"Choose a chart screenshot first."}), 400
    if tf not in {"M1","M5","M15","M30","H1","H4"}:
        tf = "M5"
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return jsonify({"error":"Server is missing GEMINI_API_KEY."}), 500
    try:
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model=os.environ.get("GEMINI_MODEL","gemini-3.6-flash"),
            contents=[SYSTEM + f"\nThe supplied XAUUSD chart is {tf}. Analyze it now.", image_part(image)],
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.12),
        )
        text=(response.text or "").strip()
        if not text:
            return jsonify({"error":"Scanner returned an empty response."}), 502
        return jsonify(json.loads(text))
    except json.JSONDecodeError:
        return jsonify({"error":"Scanner returned invalid JSON."}), 502
    except Exception as e:
        return jsonify({"error":f"Analysis failed: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",8080)))
