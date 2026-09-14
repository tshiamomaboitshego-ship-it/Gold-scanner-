import os, json, base64
from flask import Flask, request, jsonify, send_from_directory
from google import genai
from google.genai import types

app = Flask(__name__, static_folder=".", static_url_path="")

FINAL_PROMPT = """
You are Gold Scanner V6.4, an XAUUSD ENTRY-MAP assistant.

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
- For BUY: TP1 > entry area, TP2 > TP1, TP3 > TP2.
- For SELL: TP1 < entry area, TP2 < TP1, TP3 < TP2.
- NEVER allow TP1 to overlap or sit inside any active entry zone.
- If a TP overlaps an entry area or gives almost no room, set that TP to null.
- Do not invent TPs just to fill all 3.
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
