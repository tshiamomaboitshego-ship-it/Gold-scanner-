import os,json,base64
from flask import Flask,request,jsonify,send_from_directory
from google import genai
from google.genai import types
app=Flask(__name__,static_folder=".",static_url_path="")

FAST="""You are Gold Scanner V5 Fast Scan for XAUUSD. Input is ONE current M5 screenshot.
Return WAIT, POSSIBLE BUY, or POSSIBLE SELL. Keep explanations very short and simple.
Use visible structure, momentum, support/resistance, rejection and pullback behavior.
Pick ONE main zone/level only.
WAIT: say what zone to wait for. The next_action MUST be price-triggered: tell the user to scan M5 again when price reaches or enters that zone. NEVER mention minutes, hours, clock times, waiting a fixed amount of time, or "scan later".
POSSIBLE BUY/SELL: ask for H1+M15 confirmation. Do not give TP1/TP2.
Confidence means interpretation confidence, not win probability.
Return ONLY JSON:
{"signal":"WAIT|POSSIBLE BUY|POSSIBLE SELL","confidence_score":0,"trend":"Up|Down|Mixed","main_zone":null,"reason":"","next_action":""}"""

CONF="""You are Gold Scanner V5 Confirmation Scan for XAUUSD. Inputs are H1, M15, current M5.
H1=direction, M15=structure/pullback zone, M5=entry timing.
Return BUY, SELL, WAIT FOR BUY PULLBACK, WAIT FOR SELL PULLBACK, or WAIT.
Do NOT give TP1/TP2. Focus on ONE zone.
BUY/SELL: give entry_zone, invalidation, next_support_resistance, action.
WAIT FOR PULLBACK: entry_zone is the pullback zone; tell user to wait for price to enter it then rescan M5.
WAIT: choose one main_zone. The action MUST tell the user to rescan M5 when price reaches/enters that zone. NEVER use a timer, minutes, hours, or a fixed clock time.
Keep reason under 8 words. Keep action under 16 words. Never invent unreadable prices.
Return ONLY JSON:
{"signal":"BUY|SELL|WAIT FOR BUY PULLBACK|WAIT FOR SELL PULLBACK|WAIT","confidence_score":0,"trend":"Up|Down|Mixed","current_price":null,"main_zone":null,"entry_zone":null,"invalidation":null,"next_support_resistance":null,"reason":"","action":""}"""

def part(x):
    h,b=x.split(",",1); mime=h.split(";",1)[0].replace("data:","")
    return types.Part.from_bytes(data=base64.b64decode(b),mime_type=mime)
def run(contents):
    key=os.environ.get("GEMINI_API_KEY")
    if not key: raise RuntimeError("Missing GEMINI_API_KEY.")
    c=genai.Client(api_key=key)
    r=c.models.generate_content(model=os.environ.get("GEMINI_MODEL","gemini-3.6-flash"),contents=contents,config=types.GenerateContentConfig(response_mime_type="application/json",temperature=.08))
    return json.loads((r.text or "").strip())
@app.get("/")
def home(): return send_from_directory(".","index.html")
@app.get("/manifest.json")
def manifest(): return send_from_directory(".","manifest.json")
@app.get("/sw.js")
def sw(): return send_from_directory(".","sw.js")
@app.get("/icon.svg")
def icon(): return send_from_directory(".","icon.svg")
@app.post("/api/fast-scan")
def fast():
    d=request.get_json(force=True); m5=d.get("m5")
    if not str(m5).startswith("data:image/"): return jsonify({"error":"Choose M5 first."}),400
    try:return jsonify(run([FAST,part(m5)]))
    except Exception as e:return jsonify({"error":f"Fast scan failed: {e}"}),500
@app.post("/api/confirm")
def confirm():
    d=request.get_json(force=True)
    for k in ("h1","m15","m5"):
        if not str(d.get(k,"")).startswith("data:image/"): return jsonify({"error":f"Missing {k.upper()}."}),400
    try:return jsonify(run([CONF,part(d["h1"]),part(d["m15"]),part(d["m5"])]))
    except Exception as e:return jsonify({"error":f"Confirmation failed: {e}"}),500
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",8080)))
