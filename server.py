import os, json, base64
from flask import Flask, request, jsonify, send_from_directory
from google import genai
from google.genai import types

app = Flask(__name__, static_folder=".", static_url_path="")

FINAL_PROMPT = """
You are Gold Scanner V9, an XAUUSD M5-ONLY ENTRY SCANNER.

You receive ONE screenshot: the CURRENT XAUUSD M5 chart.
Do not infer or use H1, M15, H4, daily, or any higher-timeframe bias.
Focus on the current price and the most recent M5 structure on the RIGHT side of the screenshot.

GOAL:
Identify ONE fresh, still-usable M5 entry opportunity from this single scan.

Choose exactly one:
- BUY SETUP
- SELL SETUP
- NO TRADE

RULES:
1. Read the current price from the far-right price marker/current candle.
2. Give ONE tight entry zone near current price or at the next nearby M5 pullback/retest.
3. Do not return a historical entry that already triggered and moved away.
4. If price already used the candidate zone and materially progressed toward its target, reject it.
5. Do not force BUY or SELL. Use NO TRADE if M5 is messy, extended, or there is no fresh entry.
6. Use only visible M5 price action: recent swing highs/lows, support/resistance, break/retest, rejection, momentum and local structure.
7. Do not require another scan or another timeframe.
8. Return a clear invalidation PRICE LEVEL when visible, not vague wording.
9. Never claim certainty, guaranteed profit, or a win rate.

TARGETS:
BUY: TP1 > entry zone, TP2 > TP1, TP3 > TP2.
SELL: TP1 < entry zone, TP2 < TP1, TP3 < TP2.
Do not place TP1 inside the entry zone.

VISUALS:
entry y_top/y_bottom and TP y values are normalized 0.0-1.0 from the top of the M5 screenshot.
Keep the entry band tight.

Return JSON only:
{
 "signal":"BUY SETUP|SELL SETUP|NO TRADE",
 "m5_state":"short current M5 description",
 "current_price":null,
 "entry":{
   "zone":null,
   "type":null,
   "freshness":"FRESH|USED/MISSED|NONE",
   "instruction":null,
   "invalidation":null,
   "y_top":null,
   "y_bottom":null
 },
 "tp1":null,"tp1_y":null,
 "tp2":null,"tp2_y":null,
 "tp3":null,"tp3_y":null,
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
    result.setdefault("reason","No fresh entry setup found.")

    e=result.get("entry") if isinstance(result.get("entry"),dict) else {}
    for k in ("zone","type","freshness","instruction","invalidation","y_top","y_bottom"): e.setdefault(k,None)
    result["entry"]=e

    def no_trade(reason):
        result["signal"]="NO TRADE"
        result["reason"]=reason
        result["entry"]={"zone":None,"type":None,"freshness":"NONE","instruction":None,"invalidation":None,"y_top":None,"y_bottom":None}
        for n in (1,2,3):
            result[f"tp{n}"]=None; result[f"tp{n}_y"]=None
        return result

    if sig=="NO TRADE": return no_trade(result.get("reason") or "No fresh entry setup found.")
    if str(e.get("freshness") or "").upper() in {"USED","MISSED","USED/MISSED"}:
        return no_trade("Best historical setup is already used/missed; no fresh entry selected.")

    bounds=_zone_bounds(e.get("zone"))
    if bounds is None: return no_trade("No reliable fresh entry zone could be identified.")
    lo,hi=bounds

    cp=_num(result.get("current_price"))
    t1=_num(result.get("tp1")); t2=_num(result.get("tp2")); t3=_num(result.get("tp3"))

    # Hard late-entry guard: if current price has already reached/passed TP1,
    # the proposed setup is no longer actionable.
    if cp is not None and t1 is not None:
        if sig=="SELL SETUP" and cp <= t1:
            return no_trade("Setup already progressed to/past TP1; entry is used/missed.")
        if sig=="BUY SETUP" and cp >= t1:
            return no_trade("Setup already progressed to/past TP1; entry is used/missed.")

    # TP side/order validation.
    valid1=t1 is not None and ((sig=="BUY SETUP" and t1>hi) or (sig=="SELL SETUP" and t1<lo))
    if not valid1:
        for n in (1,2,3):
            result[f"tp{n}"]=None; result[f"tp{n}_y"]=None
    elif sig=="BUY SETUP":
        if t2 is not None and t2<=t1:
            result["tp2"]=result["tp2_y"]=result["tp3"]=result["tp3_y"]=None
        elif t3 is not None and t2 is not None and t3<=t2:
            result["tp3"]=result["tp3_y"]=None
    else:
        if t2 is not None and t2>=t1:
            result["tp2"]=result["tp2_y"]=result["tp3"]=result["tp3_y"]=None
        elif t3 is not None and t2 is not None and t3>=t2:
            result["tp3"]=result["tp3_y"]=None

    result["entry"]["freshness"]="FRESH"
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
