import os, json, base64
from flask import Flask, request, jsonify, send_from_directory
from google import genai
from google.genai import types

app = Flask(__name__, static_folder=".", static_url_path="")

FINAL_PROMPT = """
You are Gold Scanner V12, an XAUUSD M5 TWO-SIDED PULLBACK ZONE MAPPER.
Analyze ONE current XAUUSD M5 screenshot only. Never use or infer higher timeframes.

Do NOT choose trade direction. Map BOTH sides when visibly valid:
BUY PULLBACK = best fresh nearby support/demand/retest zone below or around current price.
SELL PULLBACK = best fresh nearby resistance/supply/retest zone above or around current price.

Focus on newest/right-edge candles and current price.
BUY evidence: recent support, demand, swing low, broken resistance retest, bullish impulse origin.
SELL evidence: recent resistance, supply, swing high, broken support retest, bearish impulse origin.
Prefer recent, nearby, fresh zones. Reject clearly used, invalidated, exhausted, or distant zones.
Do not invent a zone merely to provide both sides. A side may be null.
Do not output TP/target/take-profit levels or a trade signal. User decides direction.
Classify M5 state BULLISH, BEARISH, or UNCLEAR for context only.
y_top/y_bottom are normalized 0.0-1.0 from screenshot top.

Return JSON only:
{
 "current_price":null,
 "m5_state":"BULLISH|BEARISH|UNCLEAR",
 "m5_description":"short current/right-edge description",
 "buy_pullback":{"zone":null,"freshness":"FRESH|NONE","reason":"short reason","invalidation":null,"y_top":null,"y_bottom":null},
 "sell_pullback":{"zone":null,"freshness":"FRESH|NONE","reason":"short reason","invalidation":null,"y_top":null,"y_bottom":null},
 "note":"These are potential reaction/pullback areas, not automatic entries."
}
"""

def image_part(data_url):
    header, body = data_url.split(",", 1)
    mime = header.split(";", 1)[0].replace("data:", "")
    return types.Part.from_bytes(data=base64.b64decode(body), mime_type=mime)

def run_model(contents):
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(
        model=os.environ.get("GEMINI_MODEL", "gemini-3.6-flash"),
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.05,
        ),
    )
    return json.loads(response.text)

def _num(v):
    try:
        if v is None or isinstance(v, bool):
            return None
        return float(v)
    except (TypeError, ValueError):
        return None

def _zone_bounds(zone):
    if zone is None:
        return None
    if isinstance(zone, (int, float)):
        x = float(zone)
        return (x, x)
    import re
    nums = re.findall(r"-?\d+(?:\.\d+)?", str(zone).replace(",", ""))
    if not nums:
        return None
    vals = [float(x) for x in nums[:2]]
    if len(vals) == 1:
        return (vals[0], vals[0])
    return (min(vals), max(vals))

def _empty_watch(n):
    return {"label": f"WATCH {n}", "zone": None, "trigger": None, "y_top": None, "y_bottom": None}

def _empty_entry():
    return {"zone": None, "confirmation": None, "y_top": None, "y_bottom": None}

def normalize_result(result):
    if not isinstance(result, dict): result={}
    state=str(result.get("m5_state") or "UNCLEAR").upper()
    result["m5_state"]=state if state in {"BULLISH","BEARISH","UNCLEAR"} else "UNCLEAR"
    result.setdefault("current_price",None)
    result.setdefault("m5_description","")
    result.setdefault("note","These are potential reaction/pullback areas, not automatic entries.")
    for side in ("buy_pullback","sell_pullback"):
        z=result.get(side)
        if not isinstance(z,dict): z={}
        if str(z.get("freshness") or "NONE").upper()!="FRESH" or not z.get("zone"):
            z={"zone":None,"freshness":"NONE","reason":z.get("reason","No clear fresh zone found."),"invalidation":None,"y_top":None,"y_bottom":None}
        else:
            z["freshness"]="FRESH"; z.setdefault("reason",""); z.setdefault("invalidation",None); z.setdefault("y_top",None); z.setdefault("y_bottom",None)
        result[side]=z
    return result

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
    try:
        d = request.get_json(force=True)
        if not d.get("m5"):
            return jsonify({"error":"missing_image","detail":"M5 screenshot is required."}), 400

        result = run_model([
            FINAL_PROMPT,
            image_part(d["m5"]),
        ])
        return jsonify(normalize_result(result))

    except Exception as e:
        text = str(e)
        lower = text.lower()
        is_daily = "GenerateRequestsPerDayPerProjectPerModel-FreeTier" in text or "perday" in lower
        is_quota = "429" in text or "resource_exhausted" in lower or "quota" in lower
        return jsonify({
            "error": "quota" if is_quota else "scan_failed",
            "daily_quota": bool(is_daily),
            "detail": text[:1200]
        }), 429 if is_quota else 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
