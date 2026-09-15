import os, json, base64
from flask import Flask, request, jsonify, send_from_directory
from google import genai
from google.genai import types

app = Flask(__name__, static_folder=".", static_url_path="")

FINAL_PROMPT = """
You are Gold Scanner V13, a focused XAUUSD M5 PULLBACK FINDER.
Analyze ONLY the ONE current XAUUSD M5 screenshot supplied. Do not infer H1/M15 or unseen future candles.
Your job is NOT to predict direction and NOT to issue BUY NOW / SELL NOW signals.
Your only job is to inspect the visible M5 structure and map the best CURRENT pullback areas the user can watch.

Read the newest/right-edge candles first, then work left only as far as needed to understand the recent move.
Estimate current price from the visible chart label/scale when readable.

For a BUY pullback zone, look for the strongest fresh nearby area at/below current price supported by visible evidence such as:
- recently defended support / higher-low area,
- origin/base of a strong bullish impulse,
- resistance that was clearly broken and could be retested as support,
- fresh demand/reaction area that has not already been repeatedly consumed.

For a SELL pullback zone, look for the strongest fresh nearby area at/above current price supported by visible evidence such as:
- recently defended resistance / lower-high area,
- origin/base of a strong bearish impulse,
- support that was clearly broken and could be retested as resistance,
- fresh supply/reaction area that has not already been repeatedly consumed.

Freshness rules:
- Prefer zones created by the most recent meaningful impulse/break/retest structure.
- Prefer nearby zones over old distant zones when evidence quality is similar.
- Reject zones clearly broken through and accepted beyond, repeatedly tested/consumed, or already reacted from and moved away.
- A wick touching a zone does NOT mean an automatic entry.
- Never invent a weak opposite-side zone just to fill both sides; either side may be null.
- Keep zones reasonably tight around the actual visible structure, not huge ranges.

For each valid zone give a short basis and what the user should visually wait for: rejection plus follow-through/structure response. Do NOT give take-profit levels, position size, or an automatic trade signal.
Classify M5 state BULLISH, BEARISH, or UNCLEAR only as context; it must not force which zone is returned.

y_top/y_bottom are normalized 0.0-1.0 from screenshot top and should bracket the visible zone when possible.

Return JSON only:
{
 "current_price": null,
 "m5_state": "BULLISH|BEARISH|UNCLEAR",
 "m5_description": "short description of newest visible M5 structure",
 "buy_pullback": {
   "zone": null,
   "freshness": "FRESH|NONE",
   "reason": "why this visible area qualifies",
   "confirmation": "what bullish reaction to wait for; not an automatic entry",
   "y_top": null,
   "y_bottom": null
 },
 "sell_pullback": {
   "zone": null,
   "freshness": "FRESH|NONE",
   "reason": "why this visible area qualifies",
   "confirmation": "what bearish reaction to wait for; not an automatic entry",
   "y_top": null,
   "y_bottom": null
 },
 "note": "Zone touch = attention, not entry. Wait for a reaction and decide for yourself."
}
"""

def image_part(data_url):
    header, body = data_url.split(",", 1)
    mime = header.split(";", 1)[0].replace("data:", "")
    return types.Part.from_bytes(data=base64.b64decode(body), mime_type=mime)

def _is_fallback_error(exc):
    text = str(exc).lower()
    return (
        "503" in text
        or "unavailable" in text
        or "high demand" in text
        or "service unavailable" in text
        or "429" in text
        or "resource_exhausted" in text
        or "quota" in text
    )

def run_model(contents):
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    primary = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
    fallback = os.environ.get("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash")

    # One primary attempt. On 503/high-demand OR a per-model 429 quota error,
    # make ONE attempt on a different configured model. Never loop beyond that.
    models = [primary]
    if fallback and fallback != primary:
        models.append(fallback)

    last_error = None
    for i, model in enumerate(models):
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.05,
                ),
            )
            result = json.loads(response.text)
            if isinstance(result, dict):
                result["model_used"] = model
                result["fallback_used"] = (i > 0)
            return result
        except Exception as exc:
            last_error = exc
            # One controlled fallback only.
            if i == 0 and len(models) > 1 and _is_fallback_error(exc):
                continue
            raise

    raise last_error

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
    result.setdefault("note","Zone touch = attention, not entry. Wait for a reaction and decide for yourself.")
    for side in ("buy_pullback","sell_pullback"):
        z=result.get(side)
        if not isinstance(z,dict): z={}
        if str(z.get("freshness") or "NONE").upper()!="FRESH" or not z.get("zone"):
            z={"zone":None,"freshness":"NONE","reason":z.get("reason","No clear fresh zone found."),"confirmation":"","y_top":None,"y_bottom":None}
        else:
            z["freshness"]="FRESH"; z.setdefault("reason",""); z.setdefault("confirmation",""); z.setdefault("y_top",None); z.setdefault("y_bottom",None)
        result[side]=z
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
