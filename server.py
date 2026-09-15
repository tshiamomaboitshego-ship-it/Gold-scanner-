import os, json, base64
from flask import Flask, request, jsonify, send_from_directory
from google import genai
from google.genai import types

app = Flask(__name__, static_folder=".", static_url_path="")

FINAL_PROMPT = """
You are Gold Scanner V8, an XAUUSD ONE-SCAN ENTRY FINDER.
You receive H1, M15, then current M5 screenshots.

Goal: ONE scan should identify the best entry zone. Do NOT create a wait-then-rescan workflow.
Use H1 for broad bias, M15 for structure/setup, and M5 to refine the entry.

Return BUY SETUP, SELL SETUP, or NO TRADE.
For BUY/SELL, return ONE best entry zone, an entry instruction, an invalidation condition, and TP1/TP2/TP3 when structurally valid.
The zone may be current price or a nearby pullback/retest. The user should not need another scan when price reaches it.
If structure is genuinely unclear, use NO TRADE. Never claim certainty or guaranteed profit.

BUY targets must be above the entry zone in ascending order.
SELL targets must be below the entry zone in descending order.
Normalized y coordinates run 0.0-1.0 from the top of M5.

Return JSON only:
{
 "signal":"BUY SETUP|SELL SETUP|NO TRADE",
 "higher_timeframe_bias":"BUY|SELL|MIXED",
 "m15_setup":"short",
 "m5_state":"short",
 "current_price":null,
 "entry":{"zone":null,"type":null,"instruction":null,"invalidation":null,"y_top":null,"y_bottom":null},
 "tp1":null,"tp1_y":null,"tp2":null,"tp2_y":null,"tp3":null,"tp3_y":null,
 "reason":"short"
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
    sig=str(result.get("signal") or "NO TRADE").upper()
    if sig not in {"BUY SETUP","SELL SETUP","NO TRADE"}: sig="NO TRADE"
    result["signal"]=sig
    result.setdefault("higher_timeframe_bias","MIXED")
    result.setdefault("m15_setup","")
    result.setdefault("m5_state","")
    result.setdefault("reason","No clean entry setup found.")
    e=result.get("entry") if isinstance(result.get("entry"),dict) else {}
    for k in ("zone","type","instruction","invalidation","y_top","y_bottom"): e.setdefault(k,None)
    result["entry"]=e
    if sig=="NO TRADE" or _zone_bounds(e.get("zone")) is None:
        if sig!="NO TRADE":
            result["signal"]="NO TRADE"; result["reason"]="No reliable entry zone could be identified."
        result["entry"]={"zone":None,"type":None,"instruction":None,"invalidation":None,"y_top":None,"y_bottom":None}
        for n in (1,2,3): result[f"tp{n}"]=None; result[f"tp{n}_y"]=None
        return result
    lo,hi=_zone_bounds(e["zone"]); t1=_num(result.get("tp1")); t2=_num(result.get("tp2")); t3=_num(result.get("tp3"))
    ok=t1 is not None and ((sig=="BUY SETUP" and t1>hi) or (sig=="SELL SETUP" and t1<lo))
    if not ok:
        for n in (1,2,3): result[f"tp{n}"]=None; result[f"tp{n}_y"]=None
    elif sig=="BUY SETUP":
        if t2 is not None and t2<=t1: result["tp2"]=result["tp2_y"]=result["tp3"]=result["tp3_y"]=None
        elif t3 is not None and t2 is not None and t3<=t2: result["tp3"]=result["tp3_y"]=None
    else:
        if t2 is not None and t2>=t1: result["tp2"]=result["tp2_y"]=result["tp3"]=result["tp3_y"]=None
        elif t3 is not None and t2 is not None and t3>=t2: result["tp3"]=result["tp3_y"]=None
    return result

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
    try:
        d = request.get_json(force=True)
        if not all(d.get(k) for k in ("h1", "m15", "m5")):
            return jsonify({"error":"missing_images","detail":"H1, M15 and M5 are required."}), 400

        result = run_model([
            FINAL_PROMPT,
            image_part(d["h1"]),
            image_part(d["m15"]),
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
