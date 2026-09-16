import os, json, base64, urllib.parse, urllib.request, statistics
from flask import Flask, request, jsonify, send_from_directory
from google import genai
from google.genai import types

app = Flask(__name__, static_folder='.', static_url_path='')

PROMPT = r'''
You are Gold Scanner V15, a conservative XAUUSD M5 HYBRID PULLBACK + CONFIRMATION ANALYST.
You receive ONE current M5 screenshot plus optional deterministic M5 market-data metrics calculated by the server.
Never issue BUY NOW / SELL NOW. Never promise profit, accuracy, or a reversal.

CRITICAL CONFIRMATION RULE (fixes V14 weakness):
- HISTORICAL_REACTION means a zone visibly worked earlier but price has since moved away. It is NOT current entry confirmation.
- CURRENT_CONFIRMATION means the NEWEST visible candles are currently testing/retesting the zone and CLOSED-candle rejection + follow-through/structure evidence exists now.
- A zone far from current price can NEVER be CURRENT_CONFIRMATION just because it reacted earlier.
- If price is between zones, action_state should normally be WAIT.

READING ORDER
1) Newest/right-edge candles first; older candles are context only.
2) Prefer exact market-data metrics when data_status=LIVE_DATA. Screenshot price is secondary and may differ slightly by broker/feed.
3) Use mathematical structure metrics (swings, BOS/CHoCH, ATR, momentum) when supplied; do not contradict them without clearly stating a screenshot/data mismatch.
4) Find fresh nearby pullback zones. Penalize broken, heavily retested, consumed, distant or already-used zones.
5) Detect break-and-retest: broken support can become resistance; broken resistance can become support, but require a fresh retest.
6) Treat equal highs/lows and swing clusters only as liquidity context, never as guaranteed stop hunts.
7) Volatility/momentum matter: do not fade strong expansion merely because a level exists.
8) If event_risk is HIGH, downgrade confidence and say technical behavior can be unstable.

ZONE SCORE 0-100 = evidence quality, NOT win probability:
freshness 0-20; move-away strength 0-15; structure 0-20; limited touches 0-10; proximity 0-10; clean invalidation 0-10; momentum alignment 0-10; data agreement 0-5.
<=49 WEAK, 50-69 MODERATE, 70-84 STRONG, 85-100 VERY_STRONG.

confirmation_state must be one of:
NO_ZONE, WAIT, TESTING, REJECTION_DETECTED, CONFIRMATION_DEVELOPING, CURRENT_CONFIRMATION, HISTORICAL_REACTION, INVALIDATED.
Be conservative. If newest candle closure is uncertain, do not use CURRENT_CONFIRMATION.

Return JSON only:
{
 "current_price": null,
 "m5_state":"BULLISH|BEARISH|UNCLEAR",
 "structure":"HH_HL|LL_LH|MIXED|UNCLEAR",
 "structure_event":"BULLISH_BOS|BEARISH_BOS|BULLISH_CHOCH|BEARISH_CHOCH|NONE|UNCLEAR",
 "volatility":"LOW|NORMAL|HIGH|EXTREME",
 "momentum":"BULLISH_STRONG|BULLISH|NEUTRAL|BEARISH|BEARISH_STRONG|UNCLEAR",
 "m5_description":"short factual description",
 "buy_pullback":{"zone":null,"freshness":"FRESH|NONE","score":0,"quality":"WEAK|MODERATE|STRONG|VERY_STRONG|NONE","reason":"","confirmation_state":"NO_ZONE|WAIT|TESTING|REJECTION_DETECTED|CONFIRMATION_DEVELOPING|CURRENT_CONFIRMATION|HISTORICAL_REACTION|INVALIDATED","confirmation":"","invalidation":""},
 "sell_pullback":{"zone":null,"freshness":"FRESH|NONE","score":0,"quality":"WEAK|MODERATE|STRONG|VERY_STRONG|NONE","reason":"","confirmation_state":"NO_ZONE|WAIT|TESTING|REJECTION_DETECTED|CONFIRMATION_DEVELOPING|CURRENT_CONFIRMATION|HISTORICAL_REACTION|INVALIDATED","confirmation":"","invalidation":""},
 "liquidity_context":"short factual note or none",
 "break_retest_context":"short factual note or none",
 "risk_filter":"PASS|CAUTION|BLOCK",
 "risk_reason":"short reason",
 "action_state":"WAIT|OBSERVE_REACTION|CURRENT_CONFIRMATION_PRESENT|NO_VALID_SETUP|HIGH_RISK_EVENT",
 "note":"Analysis aid only; confirmation is not certainty."
}
'''

def image_part(data_url):
    header, body = data_url.split(',', 1)
    mime = header.split(';', 1)[0].replace('data:', '')
    return types.Part.from_bytes(data=base64.b64decode(body), mime_type=mime)

def fetch_m5():
    key=os.environ.get('TWELVE_DATA_API_KEY','').strip()
    if not key: return None, 'SCREENSHOT_ONLY', 'TWELVE_DATA_API_KEY not configured'
    q=urllib.parse.urlencode({'symbol':'XAU/USD','interval':'5min','outputsize':'120','timezone':'UTC','apikey':key})
    try:
        with urllib.request.urlopen('https://api.twelvedata.com/time_series?'+q, timeout=8) as resp:
            d=json.loads(resp.read().decode())
        vals=d.get('values') or []
        if d.get('status')=='error' or len(vals)<25: return None,'DATA_UNAVAILABLE',d.get('message','Not enough M5 candles')
        candles=[]
        for v in reversed(vals):
            candles.append({'t':v['datetime'],'o':float(v['open']),'h':float(v['high']),'l':float(v['low']),'c':float(v['close'])})
        return candles,'LIVE_DATA','Twelve Data XAU/USD 5min'
    except Exception as e:
        return None,'DATA_UNAVAILABLE',str(e)[:220]

def analytics(c):
    if not c: return {}
    trs=[]
    for i,x in enumerate(c):
        pc=c[i-1]['c'] if i else x['c']
        trs.append(max(x['h']-x['l'],abs(x['h']-pc),abs(x['l']-pc)))
    atr=sum(trs[-14:])/min(14,len(trs))
    swings_hi=[]; swings_lo=[]
    for i in range(2,len(c)-2):
        if c[i]['h']>max(c[i-2]['h'],c[i-1]['h'],c[i+1]['h'],c[i+2]['h']): swings_hi.append((i,c[i]['h']))
        if c[i]['l']<min(c[i-2]['l'],c[i-1]['l'],c[i+1]['l'],c[i+2]['l']): swings_lo.append((i,c[i]['l']))
    last=c[-1]; prev_close=c[-6]['c'] if len(c)>=6 else c[0]['c']; move=last['c']-prev_close
    bodies=[abs(x['c']-x['o']) for x in c[-5:]]; avg_body=sum(bodies)/len(bodies)
    direction=sum(1 if x['c']>x['o'] else -1 if x['c']<x['o'] else 0 for x in c[-5:])
    mom='NEUTRAL'
    if atr>0:
        if move>1.5*atr and direction>=2: mom='BULLISH_STRONG'
        elif move>0.5*atr: mom='BULLISH'
        elif move<-1.5*atr and direction<=-2: mom='BEARISH_STRONG'
        elif move<-0.5*atr: mom='BEARISH'
    structure='UNCLEAR'; event='NONE'
    if len(swings_hi)>=2 and len(swings_lo)>=2:
        hh=swings_hi[-1][1]>swings_hi[-2][1]; hl=swings_lo[-1][1]>swings_lo[-2][1]
        lh=swings_hi[-1][1]<swings_hi[-2][1]; ll=swings_lo[-1][1]<swings_lo[-2][1]
        structure='HH_HL' if hh and hl else 'LL_LH' if ll and lh else 'MIXED'
        prior_hi=swings_hi[-1][1]; prior_lo=swings_lo[-1][1]
        if last['c']>prior_hi: event='BULLISH_BOS' if structure=='HH_HL' else 'BULLISH_CHOCH'
        elif last['c']<prior_lo: event='BEARISH_BOS' if structure=='LL_LH' else 'BEARISH_CHOCH'
    recent_ranges=[x['h']-x['l'] for x in c[-20:]]
    med=statistics.median(recent_ranges) if recent_ranges else atr
    ratio=(sum(recent_ranges[-5:])/5)/(med or 1)
    vol='EXTREME' if ratio>=2.2 else 'HIGH' if ratio>=1.45 else 'LOW' if ratio<0.65 else 'NORMAL'
    eqh=[]; eql=[]; tol=max(atr*0.12,0.15)
    for arr,out in ((swings_hi,eqh),(swings_lo,eql)):
        for a,b in zip(arr[-5:-1],arr[-4:]):
            if abs(a[1]-b[1])<=tol: out.append(round((a[1]+b[1])/2,2))
    return {'data_current_price':round(last['c'],3),'atr14':round(atr,3),'structure':structure,'structure_event':event,'momentum':mom,'volatility':vol,'last_swing_highs':[round(x[1],2) for x in swings_hi[-3:]],'last_swing_lows':[round(x[1],2) for x in swings_lo[-3:]],'equal_highs':eqh[-2:],'equal_lows':eql[-2:],'recent_5bar_move':round(move,3),'avg_body_5':round(avg_body,3),'latest_closed_candles':c[-12:]}

def run_model(contents):
    client=genai.Client(api_key=os.environ['GEMINI_API_KEY'])
    model=os.environ.get('GEMINI_MODEL','gemini-3.6-flash')
    response=client.models.generate_content(model=model,contents=contents,config=types.GenerateContentConfig(response_mime_type='application/json',temperature=0.02))
    r=json.loads(response.text); r['model_used']=model; return r

def clamp(v):
    try:return max(0,min(100,int(round(float(v)))))
    except:return 0

def qual(s): return 'NONE' if s<=0 else 'WEAK' if s<50 else 'MODERATE' if s<70 else 'STRONG' if s<85 else 'VERY_STRONG'

def norm(r,metrics,data_status,event_risk):
    if not isinstance(r,dict):r={}
    if data_status=='LIVE_DATA' and metrics.get('data_current_price') is not None:r['current_price']=metrics['data_current_price']
    else:
        try:r['current_price']=float(r.get('current_price')) if r.get('current_price') is not None else None
        except:r['current_price']=None
    for k,allowed,default in [('m5_state',{'BULLISH','BEARISH','UNCLEAR'},'UNCLEAR'),('structure',{'HH_HL','LL_LH','MIXED','UNCLEAR'},'UNCLEAR'),('structure_event',{'BULLISH_BOS','BEARISH_BOS','BULLISH_CHOCH','BEARISH_CHOCH','NONE','UNCLEAR'},'UNCLEAR'),('volatility',{'LOW','NORMAL','HIGH','EXTREME'},'NORMAL'),('momentum',{'BULLISH_STRONG','BULLISH','NEUTRAL','BEARISH','BEARISH_STRONG','UNCLEAR'},'UNCLEAR')]:
        v=str(r.get(k) or default).upper(); r[k]=v if v in allowed else default
    valid={'NO_ZONE','WAIT','TESTING','REJECTION_DETECTED','CONFIRMATION_DEVELOPING','CURRENT_CONFIRMATION','HISTORICAL_REACTION','INVALIDATED'}
    cp=r.get('current_price')
    for side in ('buy_pullback','sell_pullback'):
        z=r.get(side) if isinstance(r.get(side),dict) else {}; zone=z.get('zone'); fresh=str(z.get('freshness') or 'NONE').upper()
        if fresh!='FRESH' or not zone:
            r[side]={'zone':None,'freshness':'NONE','score':0,'quality':'NONE','reason':z.get('reason') or 'No clear fresh zone.','confirmation_state':'NO_ZONE','confirmation':'','invalidation':''};continue
        s=clamp(z.get('score')); st=str(z.get('confirmation_state') or 'WAIT').upper(); st=st if st in valid else 'WAIT'
        # Hard guardrail: current confirmation requires the model to assert a current retest; distant/old reactions are historical.
        conf=(z.get('confirmation') or '').lower()
        if st=='CURRENT_CONFIRMATION' and not any(w in conf for w in ('current','newest','retest','testing','now','latest')): st='HISTORICAL_REACTION'
        z.update({'freshness':'FRESH','score':s,'quality':qual(s),'confirmation_state':st})
        for k in ('reason','confirmation','invalidation'):z.setdefault(k,'')
        r[side]=z
    act=str(r.get('action_state') or 'WAIT').upper(); allowed={'WAIT','OBSERVE_REACTION','CURRENT_CONFIRMATION_PRESENT','NO_VALID_SETUP','HIGH_RISK_EVENT'}
    if act not in allowed:act='WAIT'
    if event_risk=='HIGH':act='HIGH_RISK_EVENT';r['risk_filter']='BLOCK';r['risk_reason']='High-impact news/event mode is enabled; technical confirmation can be unstable.'
    elif act=='CURRENT_CONFIRMATION_PRESENT' and not any(r[s]['confirmation_state']=='CURRENT_CONFIRMATION' for s in ('buy_pullback','sell_pullback')):act='OBSERVE_REACTION'
    r['action_state']=act;r['data_status']=data_status;r['data_metrics']=metrics;r['event_risk']=event_risk
    r['note']='Analysis aid only. CURRENT_CONFIRMATION is not certainty or an automatic entry. Test on demo.'
    return r

@app.get('/')
def home():return send_from_directory('.','index.html')
@app.get('/manifest.json')
def manifest():return send_from_directory('.','manifest.json')
@app.get('/sw.js')
def sw():return send_from_directory('.','sw.js')
@app.get('/icon.svg')
def icon():return send_from_directory('.','icon.svg')

@app.post('/api/scan')
def scan():
    try:
        d=request.get_json(force=True)
        if not d.get('m5'):return jsonify({'error':'missing_image','detail':'M5 screenshot is required.'}),400
        event_risk='HIGH' if d.get('event_risk') else 'NORMAL'
        candles,data_status,data_note=fetch_m5(); metrics=analytics(candles)
        context={'data_status':data_status,'data_note':data_note,'deterministic_metrics':metrics,'event_risk':event_risk,'risk_budget':d.get('risk_budget')}
        result=run_model([PROMPT,'SERVER CONTEXT JSON:\n'+json.dumps(context,separators=(',',':')),image_part(d['m5'])])
        return jsonify(norm(result,metrics,data_status,event_risk))
    except Exception as e:
        text=str(e);low=text.lower();quota=('429' in text or 'resource_exhausted' in low or 'quota' in low)
        return jsonify({'error':'quota' if quota else 'scan_failed','detail':text[:1200]}),429 if quota else 500

if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.environ.get('PORT',8080)))
