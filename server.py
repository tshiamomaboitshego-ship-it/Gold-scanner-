import os, json, base64, re
from flask import Flask, request, jsonify, send_from_directory
from google import genai
from google.genai import types

app = Flask(__name__, static_folder='.', static_url_path='')

FINAL_PROMPT = r'''
You are Gold Scanner V14, a conservative XAUUSD M5 PULLBACK + CONFIRMATION ANALYST.
Analyze ONLY the ONE current XAUUSD M5 screenshot supplied. Do not infer H1/M15 or unseen future candles.
Your purpose is to map fresh pullback zones AND classify whether the newest visible price action is merely approaching/testing a zone, rejecting it, or has actually confirmed a reaction.
Never issue BUY NOW / SELL NOW instructions. Never promise a reversal, continuation, profit, or accuracy.

READING ORDER
1. Read newest/right-edge candles first. Use older visible candles only as context.
2. Read the explicit current-price label on the RIGHT EDGE only if clearly legible. Do NOT estimate current_price from a candle body or scale. If uncertain, return null.
3. Identify recent visible swing structure: HH/HL, LL/LH, or mixed/unclear.
4. Look for fresh nearby zones. Prefer recent impulse origins, defended swing areas, and clean break/retest levels.
5. Penalize/reject zones that are clearly broken and accepted beyond, heavily retested/consumed, old/distant, or already used and moved away from.

BUY ZONE evidence may include: defended support/higher low, bullish impulse origin, broken resistance retest, fresh demand.
SELL ZONE evidence may include: defended resistance/lower high, bearish impulse origin, broken support retest, fresh supply.
Do not invent an opposite zone merely to fill both sides.

ZONE SCORE (0-100) is an evidence-quality score, NOT win probability. Score using visible evidence only:
- freshness/recency 0-25
- strength of move away 0-20
- structural clarity 0-20
- limited prior touches 0-15
- proximity/relevance to current price 0-10
- clean invalidation/level clarity 0-10
Use <=49 WEAK, 50-69 MODERATE, 70-84 STRONG, 85-100 VERY_STRONG.

CONFIRMATION STATE for each zone:
- NO_ZONE: no credible fresh zone.
- WAIT: price has not reached the zone or there is no meaningful reaction.
- TESTING: newest price is currently in/around the zone but reaction candle is still forming or ambiguous.
- REJECTION_DETECTED: a visible rejection wick/body response exists, but follow-through/structure confirmation is not yet sufficient.
- CONFIRMATION_DEVELOPING: rejection plus a meaningful response exists, but newest candle/structure still needs a close or follow-through.
- CONFIRMED: visible CLOSED-candle evidence shows rejection plus follow-through/structure response away from the zone. This is still not a guaranteed trade.
- INVALIDATED: price visibly broke through and accepted beyond the zone.
Be conservative. If you cannot tell whether the newest candle is closed, do not call CONFIRMED based on that candle.

For each zone say exactly what visual event is still needed. If already CONFIRMED, state what evidence visibly confirmed it and what would invalidate that interpretation.

Return JSON only:
{
  "current_price": null,
  "m5_state": "BULLISH|BEARISH|UNCLEAR",
  "structure": "HH_HL|LL_LH|MIXED|UNCLEAR",
  "volatility": "NORMAL|HIGH|EXTREME",
  "m5_description": "short factual description",
  "buy_pullback": {
    "zone": null,
    "freshness": "FRESH|NONE",
    "score": 0,
    "quality": "WEAK|MODERATE|STRONG|VERY_STRONG|NONE",
    "reason": "visible evidence",
    "confirmation_state": "NO_ZONE|WAIT|TESTING|REJECTION_DETECTED|CONFIRMATION_DEVELOPING|CONFIRMED|INVALIDATED",
    "confirmation": "what has happened and/or what still needs to happen",
    "invalidation": "visible condition that weakens/invalidates this zone",
    "y_top": null,
    "y_bottom": null
  },
  "sell_pullback": {
    "zone": null,
    "freshness": "FRESH|NONE",
    "score": 0,
    "quality": "WEAK|MODERATE|STRONG|VERY_STRONG|NONE",
    "reason": "visible evidence",
    "confirmation_state": "NO_ZONE|WAIT|TESTING|REJECTION_DETECTED|CONFIRMATION_DEVELOPING|CONFIRMED|INVALIDATED",
    "confirmation": "what has happened and/or what still needs to happen",
    "invalidation": "visible condition that weakens/invalidates this zone",
    "y_top": null,
    "y_bottom": null
  },
  "action_state": "WAIT|OBSERVE_REACTION|CONFIRMATION_PRESENT|NO_VALID_SETUP",
  "note": "Zones and confirmation are analysis aids, not automatic entries."
}
'''

def image_part(data_url):
    header, body = data_url.split(',', 1)
    mime = header.split(';', 1)[0].replace('data:', '')
    return types.Part.from_bytes(data=base64.b64decode(body), mime_type=mime)

def run_model(contents):
    client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
    model = os.environ.get('GEMINI_MODEL', 'gemini-3.6-flash')
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(response_mime_type='application/json', temperature=0.03),
    )
    result = json.loads(response.text)
    if isinstance(result, dict): result['model_used'] = model
    return result

def clamp_score(v):
    try: return max(0, min(100, int(round(float(v)))))
    except: return 0

def quality(score):
    if score <= 0: return 'NONE'
    if score < 50: return 'WEAK'
    if score < 70: return 'MODERATE'
    if score < 85: return 'STRONG'
    return 'VERY_STRONG'

def normalize_result(r):
    if not isinstance(r, dict): r = {}
    r['m5_state'] = str(r.get('m5_state') or 'UNCLEAR').upper()
    if r['m5_state'] not in {'BULLISH','BEARISH','UNCLEAR'}: r['m5_state']='UNCLEAR'
    r['structure'] = str(r.get('structure') or 'UNCLEAR').upper()
    if r['structure'] not in {'HH_HL','LL_LH','MIXED','UNCLEAR'}: r['structure']='UNCLEAR'
    r['volatility'] = str(r.get('volatility') or 'NORMAL').upper()
    if r['volatility'] not in {'NORMAL','HIGH','EXTREME'}: r['volatility']='NORMAL'
    cp = r.get('current_price')
    try: r['current_price'] = float(cp) if cp is not None else None
    except: r['current_price'] = None
    r.setdefault('m5_description','')
    valid_states={'NO_ZONE','WAIT','TESTING','REJECTION_DETECTED','CONFIRMATION_DEVELOPING','CONFIRMED','INVALIDATED'}
    for side in ('buy_pullback','sell_pullback'):
        z = r.get(side) if isinstance(r.get(side), dict) else {}
        fresh = str(z.get('freshness') or 'NONE').upper()
        if fresh != 'FRESH' or not z.get('zone'):
            r[side]={'zone':None,'freshness':'NONE','score':0,'quality':'NONE','reason':z.get('reason') or 'No clear fresh zone found.','confirmation_state':'NO_ZONE','confirmation':'','invalidation':'','y_top':None,'y_bottom':None}
            continue
        score=clamp_score(z.get('score'))
        st=str(z.get('confirmation_state') or 'WAIT').upper()
        if st not in valid_states: st='WAIT'
        z.update({'freshness':'FRESH','score':score,'quality':quality(score),'confirmation_state':st})
        for k in ('reason','confirmation','invalidation'): z.setdefault(k,'')
        z.setdefault('y_top',None); z.setdefault('y_bottom',None)
        r[side]=z
    act=str(r.get('action_state') or 'WAIT').upper()
    if act not in {'WAIT','OBSERVE_REACTION','CONFIRMATION_PRESENT','NO_VALID_SETUP'}: act='WAIT'
    # Guardrail: never surface confirmation-present unless at least one side is explicitly confirmed.
    if act=='CONFIRMATION_PRESENT' and not any(r[s]['confirmation_state']=='CONFIRMED' for s in ('buy_pullback','sell_pullback')): act='OBSERVE_REACTION'
    r['action_state']=act
    r['note']='Zones and confirmation are analysis aids, not automatic entries. Never risk an amount that can wipe the account.'
    return r

@app.get('/')
def home(): return send_from_directory('.', 'index.html')
@app.get('/manifest.json')
def manifest(): return send_from_directory('.', 'manifest.json')
@app.get('/sw.js')
def sw(): return send_from_directory('.', 'sw.js')
@app.get('/icon.svg')
def icon(): return send_from_directory('.', 'icon.svg')

@app.post('/api/scan')
def scan():
    try:
        d=request.get_json(force=True)
        if not d.get('m5'): return jsonify({'error':'missing_image','detail':'M5 screenshot is required.'}),400
        result=run_model([FINAL_PROMPT,image_part(d['m5'])])
        return jsonify(normalize_result(result))
    except Exception as e:
        text=str(e); low=text.lower(); quota=('429' in text or 'resource_exhausted' in low or 'quota' in low)
        return jsonify({'error':'quota' if quota else 'scan_failed','detail':text[:1200]}),429 if quota else 500

if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get('PORT',8080)))
