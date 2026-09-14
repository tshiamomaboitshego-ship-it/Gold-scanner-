import os, json, base64
from flask import Flask, request, jsonify, send_from_directory
from google import genai
from google.genai import types

app = Flask(__name__, static_folder=".", static_url_path="")

FINAL_PROMPT = """
You are Gold Scanner V6.5, an XAUUSD ENTRY-MAP assistant.

Images are supplied in this order:
1) H1
2) M15
3) CURRENT M5

Your job:
- Determine higher-timeframe bias from H1 + M15.
- Determine CURRENT M5 momentum separately.
- Map up to THREE GOOD ENTRY OPPORTUNITIES on the current M5 chart.
- Give TP1/TP2/TP3 only when they make sense.
- Keep explanations short and focused on entry timing.

CORE LOGIC:
1. H1 + M15 = higher-timeframe bias.
2. M5 = current momentum + entry timing.
3. NEVER confuse bullish M5 pullback with bullish higher-timeframe bias.
4. If M5 is moving strongly against the higher-timeframe bias, do NOT mark an entry READY.
5. In that case say the M5 is a pullback/counter-move and wait for confirmation.
6. Only mark READY when M5 confirms the higher-timeframe direction.
7. If M5 structure strongly invalidates the higher-timeframe setup, return REFRESH H1/M15.
8. Do not blindly force BUY or SELL because H1/M15 say so.

ENTRY RULES:
- Return up to 3 distinct opportunities.
- entry1 = best/preferred.
- entry2 = second valid.
- entry3 = alternative/continuation if useful.
- Do NOT invent zones just to fill 3.
- Good types include pullback/retest, deeper pullback, breakout-retest, continuation, rejection.
- Each entry must include zone, type, status, confirmation, action, y_top, y_bottom.
- Status must be WATCH, WAIT CONFIRMATION, READY, MISSED, or null.
- If M5 is still moving strongly opposite to the intended trade, status cannot be READY.
- If entry is already passed and no longer usable, mark MISSED.
- Never give time-based instructions. Use price/action triggers only.

TP VALIDATION RULES:
- TP1/TP2/TP3 must be structure-based.
- For BUY: TP1 must be ABOVE every active entry it belongs to; TP2 > TP1; TP3 > TP2.
- For SELL: TP1 must be BELOW every active entry it belongs to; TP2 < TP1; TP3 < TP2.
- NEVER allow TP1 to overlap, sit inside, or sit on the wrong side of an active entry zone.
- If an entry has no sensible room to TP1, DO NOT return that entry.
- Do not invent entries or TPs just to fill all 3 slots.
- No stop loss. User manages SL and risk.

VISUAL RULES:
- y values normalized 0.0 to 1.0 from TOP of current M5 screenshot.
- Entry y_top/y_bottom should tightly hug the actual price zone.
- Avoid oversized visual bands.
- TP uses single y coordinate.
- Coordinates are approximate.
- If unreliable, use null.

TEXT LIMITS:
- higher_timeframe_reason max 8 words
- m5_reason max 8 words
- overall reason max 10 words
- each confirmation max 10 words
- each action max 10 words

Return JSON only:
{
  "signal":"BUY|SELL|WAIT|REFRESH H1/M15",
  "higher_timeframe_bias":"BUY|SELL|MIXED",
  "m5_momentum":"BULLISH|BEARISH|MIXED",
  "m5_state":"aligned|bullish pullback|bearish pullback|counter-trend|mixed",
  "trend":"Up|Down|Mixed",
  "current_price":null,
  "higher_timeframe_reason":"short",
  "m5_reason":"short",
  "reason":"very short",
  "entry1":{
    "label":"ENTRY 1",
    "zone":null,
    "type":"pullback|deep pullback|break-retest|continuation|rejection|other",
    "status":"WATCH|WAIT CONFIRMATION|READY|MISSED|null",
    "confirmation":null,
    "action":null,
    "y_top":null,
    "y_bottom":null
  },
  "entry2":{
    "label":"ENTRY 2",
    "zone":null,
    "type":"pullback|deep pullback|break-retest|continuation|rejection|other",
    "status":"WATCH|WAIT CONFIRMATION|READY|MISSED|null",
    "confirmation":null,
    "action":null,
    "y_top":null,
    "y_bottom":null
  },
  "entry3":{
    "label":"ENTRY 3",
    "zone":null,
    "type":"pullback|deep pullback|break-retest|continuation|rejection|other",
    "status":"WATCH|WAIT CONFIRMATION|READY|MISSED|null",
    "confirmation":null,
    "action":null,
    "y_top":null,
    "y_bottom":null
  },
  "tp1":null,
  "tp1_y":null,
  "tp2":null,
  "tp2_y":null,
  "tp3":null,
  "tp3_y":null
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
    """Extract two numeric bounds from strings such as '4308 - 4315'."""
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

def _empty_entry(label):
    return {
        "label": label,
        "zone": None,
        "type": None,
        "status": None,
        "confirmation": None,
        "action": None,
        "y_top": None,
        "y_bottom": None,
    }

def hard_validate_result(result):
    """
    Server-side guardrails. These checks run AFTER Gemini responds, so bad
    entry/TP combinations are removed even if the model ignores the prompt.
    """
    if not isinstance(result, dict):
        return result

    notes = []
    signal = str(result.get("signal") or "").upper()
    m5 = str(result.get("m5_momentum") or "").upper()

    # 1) Enforce TP ordering.
    tp1 = _num(result.get("tp1"))
    tp2 = _num(result.get("tp2"))
    tp3 = _num(result.get("tp3"))

    if signal == "BUY":
        if tp1 is not None and tp2 is not None and tp2 <= tp1:
            result["tp2"] = result["tp2_y"] = None
            result["tp3"] = result["tp3_y"] = None
            tp2 = tp3 = None
            notes.append("invalid TP2/TP3 removed")
        if tp2 is not None and tp3 is not None and tp3 <= tp2:
            result["tp3"] = result["tp3_y"] = None
            tp3 = None
            notes.append("invalid TP3 removed")
    elif signal == "SELL":
        if tp1 is not None and tp2 is not None and tp2 >= tp1:
            result["tp2"] = result["tp2_y"] = None
            result["tp3"] = result["tp3_y"] = None
            tp2 = tp3 = None
            notes.append("invalid TP2/TP3 removed")
        if tp2 is not None and tp3 is not None and tp3 >= tp2:
            result["tp3"] = result["tp3_y"] = None
            tp3 = None
            notes.append("invalid TP3 removed")

    # 2) Validate each entry against TP1.
    # A small minimum room avoids a target effectively sitting inside the entry.
    current = _num(result.get("current_price")) or 0.0
    min_room = max(0.5, abs(current) * 0.0001) if current else 0.5

    valid_entries = []
    removed = 0

    for i in range(1, 4):
        e = result.get(f"entry{i}")
        if not isinstance(e, dict) or not e.get("zone"):
            continue

        bounds = _zone_bounds(e.get("zone"))
        if bounds is None:
            # If the zone cannot be parsed safely, keep it but do not call it READY.
            if str(e.get("status") or "").upper() == "READY":
                e["status"] = "WAIT CONFIRMATION"
            valid_entries.append(e)
            continue

        low, high = bounds
        bad = False

        if tp1 is not None:
            if signal == "BUY":
                # TP1 must sit meaningfully above the TOP of the buy entry zone.
                bad = tp1 <= (high + min_room)
            elif signal == "SELL":
                # TP1 must sit meaningfully below the BOTTOM of the sell entry zone.
                bad = tp1 >= (low - min_room)

        if bad:
            removed += 1
            continue

        # 3) M5 timing gate: HTF bias cannot make an entry READY by itself.
        status = str(e.get("status") or "").upper()
        if status == "READY":
            if (signal == "SELL" and m5 == "BULLISH") or (signal == "BUY" and m5 == "BEARISH"):
                e["status"] = "WAIT CONFIRMATION"
                e["action"] = "Wait for M5 to turn with bias"
                notes.append("READY downgraded until M5 aligns")

        valid_entries.append(e)

    if removed:
        notes.append(f"{removed} invalid entry zone{'s' if removed != 1 else ''} removed")

    # 4) Compact remaining entries so there are no confusing gaps.
    for i in range(1, 4):
        if i <= len(valid_entries):
            e = valid_entries[i - 1]
            e["label"] = f"ENTRY {i}"
            result[f"entry{i}"] = e
        else:
            result[f"entry{i}"] = _empty_entry(f"ENTRY {i}")

    # If all entries disappear, do not present a false actionable BUY/SELL.
    if not valid_entries and signal in ("BUY", "SELL"):
        result["signal"] = "WAIT"
        result["reason"] = "No validated entry currently"
        notes.append("signal changed to WAIT")

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
