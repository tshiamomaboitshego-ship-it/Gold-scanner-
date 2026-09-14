import os, json, base64
from flask import Flask, request, jsonify, send_from_directory
from google import genai
from google.genai import types

app = Flask(__name__, static_folder=".", static_url_path="")

FINAL_PROMPT = """
You are Gold Scanner V6.7, an XAUUSD CONFIRMED-ENTRY assistant.

Images arrive in this order:
1) H1
2) M15
3) CURRENT M5

PRIMARY PURPOSE:
Do not call possible future areas "entries".
Your job is to decide whether a CONFIRMED M5 entry exists RIGHT NOW.

TIMEFRAME ROLES:
- H1 + M15 establish higher-timeframe bias/context.
- M5 controls entry timing.
- Higher-timeframe bias alone can NEVER create ENTRY READY.

VALID SIGNALS:
- ENTRY READY BUY
- ENTRY READY SELL
- NO CONFIRMED ENTRY
- REFRESH H1/M15

CONFIRMED ENTRY RULES:
- Only return ENTRY READY when current M5 visibly confirms the trade direction.
- Valid confirmation can include clear rejection + close, break/retest + hold,
  structure shift + momentum confirmation, or another strong visible M5 trigger.
- If M5 is strongly moving against the intended direction, return NO CONFIRMED ENTRY.
- Do not predict that confirmation will happen.
- Be selective: fewer signals are better than weak signals.
- Never claim certainty, guaranteed profit, or a win probability.

WATCH AREAS:
- You may return up to 3 future WATCH areas.
- WATCH areas are NOT entries.
- They only show where a setup might become valid later.
- Each watch area needs a short M5 trigger.
- Do not invent areas just to fill all 3.

WHEN ENTRY IS READY:
- Return ONE confirmed_entry zone only.
- It must be based on current M5 confirmation.
- Return a short confirmation reason.
- Return TP1/TP2/TP3 only when structurally valid.
- User manages stop loss and risk.

TP RULES:
- BUY: TP1 above confirmed entry; TP2 > TP1; TP3 > TP2.
- SELL: TP1 below confirmed entry; TP2 < TP1; TP3 < TP2.
- TP1 must not overlap confirmed entry.
- If targets are not justified, return null.

VISUAL RULES:
- y values normalized 0.0 to 1.0 from TOP of M5 screenshot.
- confirmed_entry y_top/y_bottom should tightly hug the actual price zone.
- watch area coordinates should also be tight.
- Coordinates are approximate.
- If unreliable, use null.

TEXT LIMITS:
- reason max 12 words
- confirmation max 12 words
- each watch trigger max 12 words

Return JSON only:
{
  "signal":"ENTRY READY BUY|ENTRY READY SELL|NO CONFIRMED ENTRY|REFRESH H1/M15",
  "higher_timeframe_bias":"BUY|SELL|MIXED",
  "m5_momentum":"BULLISH|BEARISH|MIXED",
  "m5_state":"aligned|bullish pullback|bearish pullback|counter-trend|mixed",
  "current_price":null,
  "reason":"short",
  "confirmed_entry":{
    "zone":null,
    "confirmation":null,
    "y_top":null,
    "y_bottom":null
  },
  "watch1":{"label":"WATCH 1","zone":null,"trigger":null,"y_top":null,"y_bottom":null},
  "watch2":{"label":"WATCH 2","zone":null,"trigger":null,"y_top":null,"y_bottom":null},
  "watch3":{"label":"WATCH 3","zone":null,"trigger":null,"y_top":null,"y_bottom":null},
  "tp1":null,"tp1_y":null,
  "tp2":null,"tp2_y":null,
  "tp3":null,"tp3_y":null
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
    """Hard guardrails after Gemini responds."""
    if not isinstance(result, dict):
        result = {}

    signal = str(result.get("signal") or "NO CONFIRMED ENTRY").upper()
    allowed = {"ENTRY READY BUY", "ENTRY READY SELL", "NO CONFIRMED ENTRY", "REFRESH H1/M15"}
    if signal not in allowed:
        signal = "NO CONFIRMED ENTRY"

    result["signal"] = signal
    result.setdefault("higher_timeframe_bias", "MIXED")
    result.setdefault("m5_momentum", "MIXED")
    result.setdefault("m5_state", "mixed")
    result.setdefault("reason", "No confirmed entry is available right now.")

    for n in range(1, 4):
        w = result.get(f"watch{n}")
        if not isinstance(w, dict):
            result[f"watch{n}"] = _empty_watch(n)
        else:
            w["label"] = f"WATCH {n}"
            w.setdefault("zone", None)
            w.setdefault("trigger", None)
            w.setdefault("y_top", None)
            w.setdefault("y_bottom", None)

    ce = result.get("confirmed_entry")
    if not isinstance(ce, dict):
        ce = _empty_entry()
    for k in ("zone", "confirmation", "y_top", "y_bottom"):
        ce.setdefault(k, None)
    result["confirmed_entry"] = ce

    m5 = str(result.get("m5_momentum") or "").upper()
    ready_buy = signal == "ENTRY READY BUY"
    ready_sell = signal == "ENTRY READY SELL"

    notes = []

    # Opposite M5 momentum blocks READY.
    if (ready_buy and m5 == "BEARISH") or (ready_sell and m5 == "BULLISH"):
        result["signal"] = "NO CONFIRMED ENTRY"
        result["confirmed_entry"] = _empty_entry()
        ready_buy = ready_sell = False
        notes.append("READY blocked because M5 momentum opposes entry")

    bounds = _zone_bounds(result["confirmed_entry"].get("zone"))
    if (ready_buy or ready_sell) and bounds is None:
        result["signal"] = "NO CONFIRMED ENTRY"
        result["confirmed_entry"] = _empty_entry()
        ready_buy = ready_sell = False
        notes.append("READY removed because confirmed zone is missing")

    tp1 = _num(result.get("tp1"))
    tp2 = _num(result.get("tp2"))
    tp3 = _num(result.get("tp3"))

    # TPs only exist for an actionable confirmed entry.
    if not (ready_buy or ready_sell):
        for n in (1, 2, 3):
            result[f"tp{n}"] = None
            result[f"tp{n}_y"] = None
    else:
        low, high = bounds
        bad_tp1 = (ready_buy and (tp1 is None or tp1 <= high)) or (ready_sell and (tp1 is None or tp1 >= low))
        if bad_tp1:
            for n in (1, 2, 3):
                result[f"tp{n}"] = None
                result[f"tp{n}_y"] = None
            notes.append("Invalid targets removed")
        else:
            if ready_buy:
                if tp2 is not None and tp2 <= tp1:
                    result["tp2"] = result["tp2_y"] = None
                    result["tp3"] = result["tp3_y"] = None
                elif tp3 is not None and tp2 is not None and tp3 <= tp2:
                    result["tp3"] = result["tp3_y"] = None
            if ready_sell:
                if tp2 is not None and tp2 >= tp1:
                    result["tp2"] = result["tp2_y"] = None
                    result["tp3"] = result["tp3_y"] = None
                elif tp3 is not None and tp2 is not None and tp3 >= tp2:
                    result["tp3"] = result["tp3_y"] = None

    result["validation_note"] = " · ".join(dict.fromkeys(notes)) if notes else ""
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
