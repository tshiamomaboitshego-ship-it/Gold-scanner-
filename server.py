import os, json, base64
from flask import Flask, request, jsonify, send_from_directory
from google import genai
from google.genai import types

app = Flask(__name__, static_folder=".", static_url_path="")

FAST_PROMPT = """You are Gold Scanner V4 Fast Scan for XAUUSD.
You receive ONE M5 screenshot. This is a screening stage, not final multi-timeframe confirmation.

Analyze visible M5 structure, momentum, support/resistance, breakout/retest, rejection and current price.
Return one of:
- WAIT: no worthwhile setup is developing.
- POSSIBLE BUY: M5 has a promising long setup worth checking against M15/H1.
- POSSIBLE SELL: M5 has a promising short setup worth checking against M15/H1.

Do NOT issue a final BUY/SELL from this stage.
Pick ONE main level/zone to watch. If WAIT, tell the user exactly when to scan M5 again.
If POSSIBLE BUY/SELL, tell the user to add M15 and H1 for confirmation.
Confidence is confidence in interpretation, not win probability.
Use only readable prices. Never invent precision.

Return ONLY JSON:
{
 "stage":"FAST",
 "signal":"WAIT|POSSIBLE BUY|POSSIBLE SELL",
 "confidence_score":0,
 "trend":"Bullish|Bearish|Neutral/Mixed",
 "market_state":"Trending|Pullback|Range|Breakout|Reversal watch|Unclear|Market closed",
 "current_price":null,
 "main_level_to_watch":null,
 "next_action":"",
 "reasons":["...","..."]
}"""

CONFIRM_PROMPT = """You are Gold Scanner V4 Confirmation Scan for XAUUSD.
You receive H1, M15 and the CURRENT M5 screenshot.
H1 = higher-timeframe direction and major structure.
M15 = setup context, support/resistance and breakout/retest structure.
M5 = current entry confirmation.

Combine all three into ONE final plan. Do not give the user separate competing levels for each timeframe.
Return BUY, SELL or WAIT. Prefer WAIT if the timeframes conflict, price is extended, at a major barrier,
ranging/choppy, market closed, or entry confirmation is weak.

For BUY/SELL return ONE main level/zone, entry zone, stop loss, TP1, TP2, approximate risk/reward,
and one short trade plan.
For WAIT return ONE main level/zone only, and one precise condition telling the user when to refresh M5
and confirm again. Avoid making them retake H1/M15 unless the higher-timeframe structure has clearly become stale.
Confidence means confidence in interpretation, not win probability.
Use only readable visible prices.

Return ONLY JSON:
{
 "stage":"CONFIRMED",
 "signal":"BUY|SELL|WAIT",
 "confidence_score":0,
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

def part(data_url):
    header, encoded = data_url.split(",", 1)
    mime = header.split(";",1)[0].replace("data:","")
    return types.Part.from_bytes(data=base64.b64decode(encoded), mime_type=mime)

def gemini(contents, temperature=.1):
    key=os.environ.get("GEMINI_API_KEY")
    if not key: raise RuntimeError("Server is missing GEMINI_API_KEY.")
    client=genai.Client(api_key=key)
    r=client.models.generate_content(
        model=os.environ.get("GEMINI_MODEL","gemini-3.6-flash"),
        contents=contents,
        config=types.GenerateContentConfig(response_mime_type="application/json", temperature=temperature),
    )
    text=(r.text or "").strip()
    if not text: raise RuntimeError("Scanner returned an empty response.")
    return json.loads(text)

@app.get("/")
def home(): return send_from_directory(".", "index.html")
@app.get("/manifest.json")
def manifest(): return send_from_directory(".", "manifest.json")
@app.get("/sw.js")
def sw(): return send_from_directory(".", "sw.js")
@app.get("/icon.svg")
def icon(): return send_from_directory(".", "icon.svg")

@app.post("/api/fast-scan")
def fast_scan():
    d=request.get_json(force=True)
    if not str(d.get("m5","")).startswith("data:image/"):
        return jsonify({"error":"Choose an M5 screenshot first."}),400
    try:
        return jsonify(gemini([FAST_PROMPT, part(d["m5"])]))
    except Exception as e:
        return jsonify({"error":f"Fast scan failed: {e}"}),500

@app.post("/api/confirm")
def confirm():
    d=request.get_json(force=True)
    for k in ("h1","m15","m5"):
        if not str(d.get(k,"")).startswith("data:image/"):
            return jsonify({"error":f"Missing {k.upper()} screenshot."}),400
    try:
        return jsonify(gemini([
            CONFIRM_PROMPT + "\nAnalyze screenshots in this exact order: H1, M15, current M5.",
            part(d["h1"]), part(d["m15"]), part(d["m5"])
        ]))
    except Exception as e:
        return jsonify({"error":f"Confirmation scan failed: {e}"}),500

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",8080)))
