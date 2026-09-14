import os, json, base64
from flask import Flask, request, jsonify, send_from_directory
from google import genai
from google.genai import types

app = Flask(__name__, static_folder=".", static_url_path="")

FAST_PROMPT = """
You are an XAUUSD M5 ENTRY-TIMING scanner.

Goal:
- Help the trader time entries, not predict blindly.
- Find ONE useful pullback/entry zone.
- If price is not at the zone yet, say WAIT FOR ZONE.
- If price is in the zone but confirmation is missing, say WAIT FOR CONFIRMATION.
- If price is in the zone and a clean M5 trigger exists, say ENTRY READY BUY or ENTRY READY SELL.
- If structure is unclear, say WAIT.
- If the current M5 looks materially different from previously expected direction, say REFRESH H1/M15.

Provide up to THREE sensible take-profit zones: TP1, TP2, TP3.
Do NOT provide a stop loss; the trader manages SL.
TP zones must follow visible support/resistance/structure, not arbitrary distances.
Also estimate each TP zone's vertical position on THIS M5 screenshot using normalized 0.0-1.0 y coordinates.
If a TP cannot be justified or located reliably, return null for that TP and its y coordinate.

Return ONE zone only.
Also estimate the vertical location of the zone on THIS screenshot so the frontend can draw a red/green band.
zone_y_top and zone_y_bottom must be numbers from 0.0 to 1.0 measured from the TOP of the image.
Example: 0.30 means 30% down from the image top.
If you cannot locate the zone reliably, use null for both.

Keep reason under 9 words.
Keep trigger under 12 words.
Keep action under 15 words.
No timer-based instructions. Rescan based on price reaching the zone or confirmation appearing.

JSON only:
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

CONFIRM_PROMPT = """
You are the FINAL XAUUSD ENTRY-TIMING scanner.

You are given H1, M15, then a CURRENT M5 screenshot.
Use:
- H1 mainly for broad direction.
- M15 for structure and the best pullback/entry area.
- M5 for exact timing.

Your job is ENTRY TIMING.
Provide up to THREE sensible take-profit zones: TP1, TP2, TP3.
Do NOT provide a stop loss; the trader manages SL.
TPs must be based on visible H1/M15/M5 structure and ordered from nearest to furthest target.
Estimate each TP's vertical position on the CURRENT M5 screenshot as 0.0-1.0 from image top.
If a TP is not justified or cannot be located reliably, return null.
Do not force the old H1/M15 bias if current M5 clearly contradicts it.
If the higher-timeframe context may be stale or invalid, return REFRESH H1/M15.

Allowed signals:
- WAIT FOR ZONE
- WAIT FOR CONFIRMATION
- ENTRY READY BUY
- ENTRY READY SELL
- WAIT
- REFRESH H1/M15

Rules:
1. ONE entry zone only.
2. If price is outside the zone -> WAIT FOR ZONE.
3. If price is inside the zone but trigger is not confirmed -> WAIT FOR CONFIRMATION.
4. ENTRY READY only when price is in/very near the zone AND M5 shows a clean confirmation.
5. Never tell the trader to enter just because price touched the zone.
6. No TP/SL fields.
7. No fixed-minute rescan instructions.
8. Keep reason under 9 words.
9. Keep trigger under 12 words.
10. Keep action under 15 words.
11. Estimate where the zone lies vertically on the CURRENT M5 screenshot:
   zone_y_top and zone_y_bottom are 0.0-1.0 from image top.
   If uncertain, return null.

JSON only:
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

@app.post("/api/fast-scan")
def fast_scan():
    d = request.get_json(force=True)
    try:
        return jsonify(run_model([FAST_PROMPT, image_part(d["m5"])]))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.post("/api/confirm")
def confirm():
    d = request.get_json(force=True)
    try:
        return jsonify(run_model([
            CONFIRM_PROMPT,
            image_part(d["h1"]),
            image_part(d["m15"]),
            image_part(d["m5"]),
        ]))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
