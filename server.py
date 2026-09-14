import os, json, base64
from flask import Flask, request, jsonify, send_from_directory
from google import genai
from google.genai import types

app = Flask(__name__, static_folder=".", static_url_path="")

FINAL_PROMPT = """
You are Gold Scanner V6.3, an XAUUSD ENTRY-MAP assistant.
Images are supplied in this order: 1) H1 2) M15 3) CURRENT M5.
Your main job is to identify the best current trade direction, map up to THREE GOOD ENTRY ZONES/opportunities on the current M5 chart, and give TP1/TP2/TP3. Keep explanations very short. Do NOT explain the whole chart.
Use H1 and M15 only as background context. Use M5 to time entries.
ENTRY ZONE RULES:
1. Return up to 3 distinct opportunities: entry1 best/preferred, entry2 second valid, entry3 alternative/continuation if useful.
2. Do NOT invent zones just to fill all 3. Use null if fewer good zones exist.
3. Prefer different valid paths such as pullback/retest, deeper pullback, breakout+retest/continuation.
4. Every entry includes price zone/trigger, type, M5 confirmation required, normalized y_top/y_bottom.
5. Zone is not an automatic entry.
6. If price clearly moved beyond an entry and it is no longer usable, status MISSED.
7. Approaching zone = WATCH.
8. In/near zone but no confirmation = WAIT CONFIRMATION.
9. Clean confirmation = READY.
10. If unclear, signal WAIT.
11. If current M5 strongly invalidates higher-timeframe context, signal REFRESH H1/M15.
12. Never use timer-based rescan instructions.
TP RULES: Return up to 3 structure-based TP targets ordered nearest to furthest. Use null if not justified. No stop loss.
VISUAL RULES: y values normalized 0.0-1.0 from TOP of CURRENT M5 screenshot. Coordinates approximate; null if unreliable.
TEXT LIMITS: overall reason max 10 words; each confirmation/action max 10 words.
Return JSON only:
{
  "signal":"BUY|SELL|WAIT|REFRESH H1/M15",
  "trend":"Up|Down|Mixed",
  "current_price":null,
  "reason":"very short",
  "entry1":{"label":"ENTRY 1","zone":null,"type":"pullback|deep pullback|break-retest|continuation|rejection|other","status":"WATCH|WAIT CONFIRMATION|READY|MISSED|null","confirmation":null,"action":null,"y_top":null,"y_bottom":null},
  "entry2":{"label":"ENTRY 2","zone":null,"type":"pullback|deep pullback|break-retest|continuation|rejection|other","status":"WATCH|WAIT CONFIRMATION|READY|MISSED|null","confirmation":null,"action":null,"y_top":null,"y_bottom":null},
  "entry3":{"label":"ENTRY 3","zone":null,"type":"pullback|deep pullback|break-retest|continuation|rejection|other","status":"WATCH|WAIT CONFIRMATION|READY|MISSED|null","confirmation":null,"action":null,"y_top":null,"y_bottom":null},
  "tp1":null,"tp1_y":null,"tp2":null,"tp2_y":null,"tp3":null,"tp3_y":null
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
