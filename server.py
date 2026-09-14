import os, json, base64
from flask import Flask, request, jsonify, send_from_directory
from google import genai
from google.genai import types

app = Flask(__name__, static_folder=".", static_url_path="")

FINAL_PROMPT = """
You are Gold Scanner V6.2, an XAUUSD ENTRY-TIMING assistant.

Images are supplied in this order:
1) H1
2) M15
3) CURRENT M5

Purpose:
- H1 = broad direction
- M15 = structure and pullback area
- M5 = exact timing
- Use ONE AI request to produce the entire result.

Allowed signals:
- WAIT FOR ZONE
- WAIT FOR CONFIRMATION
- ENTRY READY BUY
- ENTRY READY SELL
- WAIT
- REFRESH H1/M15

Entry rules:
1. Find ONE entry/pullback zone.
2. If price has not reached it -> WAIT FOR ZONE.
3. If price is in the zone but trigger is missing -> WAIT FOR CONFIRMATION.
4. ENTRY READY only when M5 shows a clean confirmation in/very near the zone.
5. Never enter merely because price touched a zone.
6. If current M5 clearly invalidates the saved H1/M15 context -> REFRESH H1/M15.
7. No timer-based rescan instructions.

Take-profit rules:
- Provide up to THREE sensible TP targets based on visible structure.
- Order TP1 nearest, TP3 furthest.
- If a TP is not justified, return null.
- Do NOT provide a stop loss. The user manages SL and risk.

Visual overlay rules:
- Estimate the vertical position of the entry zone on the CURRENT M5 screenshot.
- zone_y_top / zone_y_bottom are normalized 0.0-1.0 from the top of the M5 image.
- Estimate each TP vertical y position on CURRENT M5 as 0.0-1.0.
- If not reliable, use null.
- These coordinates are approximate.

Text:
- reason max 8 words
- trigger max 12 words
- action max 15 words

Return JSON only:
{
  "signal":"WAIT FOR ZONE|WAIT FOR CONFIRMATION|ENTRY READY BUY|ENTRY READY SELL|WAIT|REFRESH H1/M15",
  "trend":"Up|Down|Mixed",
  "current_price":null,
  "entry_zone":"price range or null",
  "zone_y_top":null,
  "zone_y_bottom":null,
  "setup_type":"pullback|break-retest|rejection|structure shift|other",
  "tp1":null,
  "tp1_y":null,
  "tp2":null,
  "tp2_y":null,
  "tp3":null,
  "tp3_y":null,
  "trigger":"short M5 confirmation needed",
  "reason":"very short reason",
  "action":"very short next action"
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
