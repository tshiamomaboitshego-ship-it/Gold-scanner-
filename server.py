import os, json
from flask import Flask, request, jsonify, send_from_directory
from openai import OpenAI

app = Flask(__name__, static_folder=".", static_url_path="")
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

SYSTEM = """You are Gold Scanner V1, a conservative XAUUSD chart-analysis assistant.
The user supplies three screenshots of the SAME market context:
- H1: determine higher-timeframe direction and major structure.
- M15: determine setup, support/resistance, consolidation, breakout/retest context.
- M5: determine entry confirmation or lack of confirmation.

Return BUY, SELL, or WAIT. WAIT is preferred when evidence conflicts, price is ranging/choppy, screenshots are unclear, market is closed, or a clean entry is absent.
Do not claim a win probability. 'confidence_score' is only confidence in the chart interpretation, 0-100.
Use visible prices only; never invent precision that cannot be read from the screenshot.
If an entry is not justified, use null for entry/SL/TP and explain why.
For BUY/SELL, propose conservative entry zone, stop loss, TP1, TP2 and approximate risk/reward based on visible structure.
Return ONLY JSON with this shape:
{
  "signal":"BUY|SELL|WAIT",
  "confidence_score":0,
  "trend":"Bullish|Bearish|Neutral/Mixed",
  "market_state":"Trending|Pullback|Range|Breakout|Reversal watch|Unclear|Market closed",
  "entry_zone":null,
  "stop_loss":null,
  "tp1":null,
  "tp2":null,
  "risk_reward":null,
  "reasons":["...","..."]
}
"""

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
    if not os.environ.get("OPENAI_API_KEY"):
        return "Server is missing OPENAI_API_KEY.", 500
    data = request.get_json(force=True)
    for k in ("h1","m15","m5"):
        if k not in data or not str(data[k]).startswith("data:image/"):
            return f"Missing or invalid {k} screenshot.", 400

    content = [
        {"type":"input_text","text":"Analyze these XAUUSD screenshots. Image order: H1, M15, M5."},
        {"type":"input_image","image_url":data["h1"],"detail":"high"},
        {"type":"input_image","image_url":data["m15"],"detail":"high"},
        {"type":"input_image","image_url":data["m5"],"detail":"high"},
    ]
    resp = client.responses.create(
        model=os.environ.get("OPENAI_MODEL","gpt-5"),
        instructions=SYSTEM,
        input=[{"role":"user","content":content}]
    )
    text = resp.output_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"): text = text[4:].strip()
    try:
        result = json.loads(text)
    except Exception:
        return jsonify({"error":"Model returned non-JSON output","raw":text}), 502
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
