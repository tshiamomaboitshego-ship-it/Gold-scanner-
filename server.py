import os, json, base64
from flask import Flask, request, jsonify, send_from_directory
from google import genai
from google.genai import types

app = Flask(__name__, static_folder=".", static_url_path="")

FINAL_PROMPT = """
You are Gold Scanner V6.6, an XAUUSD CONFIRMED-ENTRY assistant.

Images arrive in this order: H1, M15, CURRENT M5.

PRIMARY GOAL:
Do NOT present possible future price areas as actual entries.
Your most important question is:
"Is there a sufficiently confirmed M5 entry RIGHT NOW?"

TIMEFRAME ROLES:
- H1 + M15 establish higher-timeframe bias/context.
- M5 controls actual entry timing.
- A higher-timeframe bias alone is NEVER enough to create ENTRY READY.

OUTPUT STATES:
1) ENTRY READY BUY
2) ENTRY READY SELL
3) NO CONFIRMED ENTRY
4) REFRESH H1/M15

CONFIRMED ENTRY REQUIREMENTS:
- The trade direction must make sense with H1/M15 context.
- Current M5 must show actual confirmation, not merely approach a possible zone.
- Confirmation can include a clear rejection + close, break/retest + hold,
  momentum shift with structure confirmation, or another visibly strong M5 trigger.
- Do not mark READY while M5 is strongly moving against the intended direction.
- Do not predict that confirmation will happen.
- If confirmation is absent or ambiguous, return NO CONFIRMED ENTRY.
- Be selective. Fewer signals are preferred to weak signals.
- Never claim certainty, guaranteed profit, or a win probability.

WATCH AREAS:
- You may return up to 3 watch areas for what could become a setup later.
- Call them WATCH 1 / WATCH 2 / WATCH 3, NEVER ENTRY 1/2/3.
- Watch areas are informational only and must not be presented as places to enter automatically.
- Give a short trigger describing what M5 must do there.
- Do not invent watch areas to fill all slots.

WHEN ENTRY IS READY:
- Return ONE precise confirmed_entry zone only.
- It must be based on current M5 confirmation.
- Return a short confirmation reason.
- Return TP1/TP2/TP3 only when structurally valid.
- No stop loss; user manages SL/risk.

TP RULES:
- BUY: TP1 above confirmed entry; TP2 > TP1; TP3 > TP2.
- SELL: TP1 below confirmed entry; TP2 < TP1; TP3 < TP2.
- Never overlap TP1 with confirmed entry.
- Use null when a target is not justified.

VISUALS:
- All y values are normalized 0.0–1.0 from image top.
- confirmed_entry y_top/y_bottom must tightly match the M5 price area.
- Watch areas should also be tight.
- Coordinates are approximate; use null if unreliable.

TEXT:
- Keep every explanation short.
- Focus on what must happen for an actual entry.

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
        if v is None or isinstance(v, bool): return None
        return float(v)
    except (TypeError, ValueError):
        return None

def _zone_bounds(zone):
    import re
    if zone is None: return None
    nums = re.findall(r"-?\d+(?:\.\d+)?", str(zone).replace(",", ""))
    if not nums: return None
    vals = [float(x) for x in nums[:2]]
    return (vals[0], vals[0]) if len(vals)==1 else (min(vals), max(vals))

def hard_validate_result(result):
    if not isinstance(result, dict): return result
    notes=[]
    signal=str(result.get("signal") or "").upper()
    m5=str(result.get("m5_momentum") or "").upper()
    ce=result.get("confirmed_entry")
    if not isinstance(ce, dict):
        ce={"zone":None,"confirmation":None,"y_top":None,"y_bottom":None}
        result["confirmed_entry"]=ce

    ready_buy = signal=="ENTRY READY BUY"
    ready_sell = signal=="ENTRY READY SELL"

    # Hard timing gate: opposite M5 momentum can never be READY.
    if (ready_sell and m5=="BULLISH") or (ready_buy and m5=="BEARISH"):
        result["signal"]="NO CONFIRMED ENTRY"
        ce.update({"zone":None,"confirmation":None,"y_top":None,"y_bottom":None})
        notes.append("entry blocked because M5 is not aligned")
        ready_buy=ready_sell=False

    bounds=_zone_bounds(ce.get("zone"))
    if (ready_buy or ready_sell) and bounds is None:
        result["signal"]="NO CONFIRMED ENTRY"
        ce.update({"zone":None,"confirmation":None,"y_top":None,"y_bottom":None})
        notes.append("entry removed because no precise confirmed zone")
        ready_buy=ready_sell=False

    tp1=_num(result.get("tp1")); tp2=_num(result.get("tp2")); tp3=_num(result.get("tp3"))

    # If no confirmed entry, TPs are not actionable and are hidden.
    if not (ready_buy or ready_sell):
        for n in (1,2,3):
            result[f"tp{n}"]=None
            result[f"tp{n}_y"]=None
    else:
        low,high=bounds
        if ready_buy and (tp1 is None or tp1 <= high):
            result["tp1"]=result["tp1_y"]=None
            result["tp2"]=result["tp2_y"]=None
            result["tp3"]=result["tp3_y"]=None
            notes.append("invalid BUY targets removed")
        elif ready_sell and (tp1 is None or tp1 >= low):
            result["tp1"]=result["tp1_y"]=None
            result["tp2"]=result["tp2_y"]=None
            result["tp3"]=result["tp3_y"]=None
            notes.append("invalid SELL targets removed")
        else:
            if ready_buy:
                if tp2 is not None and tp2 <= tp1:
                    result["tp2"]=result["tp2_y"]=result["tp3"]=result["tp3_y"]=None
                elif tp3 is not None and tp2 is not None and tp3 <= tp2:
                    result["tp3"]=result["tp3_y"]=None
            if ready_sell:
                if tp2 is not None and tp2 >= tp1:
                    result["tp2"]=result["tp2_y"]=result["tp3"]=result["tp3_y"]=None
                elif tp3 is not None and tp2 is not None and tp3 >= tp2:
                    result["tp3"]=result["tp3_y"]=None

    result["validation_note"]=" · ".join(dict.fromkeys(notes)) if notes else ""
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
    d = request.get_json(force=True)
    try:
        result = run_model([
            FINAL_PROMPT,
            image_part(d["h1"]),
            image_part(d["m15"]),
            image_part(d["m5"]),
        ])
        result = hard_validate_result(result)
        return jsonify(result)
    except Exception as e:
        text = str(e)
        # Return a compact structured error so the app can distinguish a daily quota.
        is_daily = "GenerateRequestsPerDayPerProjectPerModel-FreeTier" in text or "PerDay" in text
        is_quota = "429" in text or "RESOURCE_EXHAUSTED" in text or "quota" in text.lower()
        return jsonify({
            "error": "quota" if is_quota else "scan_failed",
            "daily_quota": bool(is_daily),
            "detail": text[:1000]
        }), 429 if is_quota else 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
