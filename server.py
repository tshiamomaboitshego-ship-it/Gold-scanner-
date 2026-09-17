import os, json, base64, urllib.parse, urllib.request, statistics
from flask import Flask, request, jsonify, send_from_directory
from google import genai
from google.genai import types

app = Flask(__name__, static_folder='.', static_url_path='')

PROMPT = r'''
You are Gold Scanner V24, a conservative XAUUSD M5 HYBRID PULLBACK + CONFIRMATION ANALYST.
You receive ONE current M5 screenshot plus deterministic H1/M15/M5 market-data metrics fetched automatically from Twelve Data. Use H1/M15 OHLC context internally as confluence/context, but M5 remains the execution timeframe. H1/M15 must NOT automatically veto a valid M5 setup.
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
8) If event_risk is HIGH, downgrade confidence and say technical behavior can be unstable.\n9) If saved_htf_context exists, use H1 for broad structure/major zones and M15 for intermediate structure/nearby zones. Do not dump HTF analysis into the user output; use it to improve M5 zone selection and conflict detection.\n10) If saved context is marked stale by the client, reduce reliance on it.

ZONE SCORE 0-100 = evidence quality, NOT win probability:
freshness 0-20; move-away strength 0-15; structure 0-20; limited touches 0-10; proximity 0-10; clean invalidation 0-10; momentum alignment 0-10; data agreement 0-5.
<=49 WEAK, 50-69 MODERATE, 70-84 STRONG, 85-100 VERY_STRONG.

confirmation_state must be one of:
NO_ZONE, WAIT, TESTING, REJECTION_DETECTED, CONFIRMATION_DEVELOPING, CURRENT_CONFIRMATION, HISTORICAL_REACTION, INVALIDATED.
Be conservative. If newest candle closure is uncertain, do not use CURRENT_CONFIRMATION.

V20 PROTECTION + STATE RULES:
- Separate CURRENT M5 PRESSURE from a future pullback zone. A BUY zone may coexist with bearish current pressure and vice versa.
- market_phase must classify TRENDING, PULLBACK, RANGING, BREAKOUT, REVERSAL_DEVELOPING, EVENT_SHOCK, or UNCLEAR.
- If deterministic shock_detector is TRIGGERED, normal counter-momentum zone logic is suspended unless price has stabilized; action_state=VOLATILITY_PAUSE and risk_filter=BLOCK.
- approach_speed describes how aggressively price is moving toward a zone. FAST/EXTREME approach against a zone weakens it; an extreme displacement smashing into/through a zone invalidates or blocks it.
- CLOSED-candle acceptance beyond a zone/invalidation is more important than a wick. Mark broken zones INVALIDATED, never WAIT.
- If saved H1/M15 context is materially stale or deterministic HTF structure conflicts with it after a shock/major break, set htf_refresh_needed=true and explain which timeframe needs refresh.
- data_ai_conflict must explicitly report agreement/disagreement between deterministic metrics and screenshot interpretation. Strong disagreement => conservative WAIT/NO_VALID_SETUP.
- score_components must explain the evidence score (freshness, move_away, structure, touches, proximity, invalidation, momentum, data_agreement).
- setup_memory from the client contains prior zones/states. Continue their lifecycle rather than treating every screenshot as a blank slate.
- automatic_event_status may be supplied by the server. If HIGH, use HIGH_RISK_EVENT. If UNKNOWN, never pretend the calendar is clear; shock detection remains active.
- Do not call a zone failure a bad prediction when the zone was never confirmed. Distinguish NOT_TRIGGERED, TESTED, CONFIRMED, INVALIDATED.

V18 EXTRA RULES:
- zone_lifecycle: FRESH, TESTING, REACTED, RETESTED, CONSUMED, INVALIDATED, EXPIRED. Never treat REACTED/CONSUMED as a fresh setup.
- Detect displacement and FVG/imbalance only as supporting evidence.
- Detect support/resistance role flips, fake breaks/reclaims, and setup conflicts.
- Use ATR-relative proximity. If confirmation arrives after price is already extended, set too_late=true and action_state=NO_VALID_SETUP. Do not chase.
- Prefer at most the strongest nearby BUY and SELL zone; do not clutter output.
- Session context is descriptive evidence, not a reason by itself to trade.
- If spread_cost supplied is unusually high relative to ATR, risk_filter should be CAUTION/BLOCK.
- risk_budget is a cap, not a trade recommendation.

V18 MULTI-TIMEFRAME ARCHITECTURE:
- multi_timeframe_metrics contains deterministic M5, M15 and H1 calculations from deeper OHLC history when LIVE/PARTIAL data is available. Use it even if screenshot zoom hides older structure.
- H1 = broad context and major zones; M15 = intermediate context; M5 = execution. Higher timeframes add evidence but never automatically force direction.
- Evaluate BUY CASE and SELL CASE independently on every scan. A bullish H1 recovery must not suppress a valid developing M15/M5 sell case, and vice versa. Output BUY only, SELL only, BOTH, or neither based on evidence.
- Distinguish long-term trend, current recovery/pullback, and newest execution momentum. Do not label a recovery as a full structural reversal unless structure evidence supports it.
- Prefer exact OHLC highs/lows for structure and zone boundaries when data exists; use Gemini screenshot vision as visual second opinion.
- If screenshot interpretation conflicts with deterministic data, set setup_conflict=MIXED_SIGNALS and be conservative.
- Use only CLOSED-candle structure evidence from deterministic metrics; do not call an intrabar wick a BOS/CHoCH.
- H1 and M15 screenshots are preferably LANDSCAPE to maximize broad historical context. The fresh M5 screenshot is preferably PORTRAIT so newest execution candles, wicks, rejection and local structure are larger and easier to inspect. Do not penalize other orientations; deep OHLC data should reduce dependence on screenshot field-of-view.
- Saved H1/M15 screenshot context is supplementary. If live higher-timeframe OHLC materially conflicts with saved screenshot context, reduce reliance on saved context and request refresh in m5_description, but still complete the M5 analysis.

V21 PRICE-ACTION CONFLUENCE RULES:
- Use deterministic order_blocks as evidence only. FRESH/MITIGATED blocks can support a zone; BREAKER means the original block failed and may act as flipped context. Never treat every opposite candle as an order block.
- Use fvg_quality rather than raw FVG presence. Prefer fresh/unfilled, displacement-aligned imbalances; filled/old FVGs carry little weight.
- Recognize sequences, not isolated labels: liquidity sweep/reclaim -> displacement -> BOS/CHoCH -> FVG -> retracement is stronger evidence than any single component.
- premium_discount is location context only. Discount is not automatically bullish and premium is not automatically bearish.
- Distinguish external_liquidity from internal_liquidity. Liquidity levels are objectives/context, not guaranteed stop hunts.
- Use session_liquidity/opening ranges descriptively. Session levels never force a direction.
- body_acceptance is more important than a single wick: repeated closed-candle acceptance through structure weakens/invalidate opposing zones; wick sweep + reclaim is different.
- confluence_cluster must explain supporting AND opposing evidence. Do not inflate confidence by double-counting correlated concepts.
- V22 TIMING: explicitly distinguish UNTESTED future zone, ACTIVE_TEST, ALREADY_REACTED, RETEST_PENDING and INVALIDATED. Never call a recently touched/rejected zone FRESH.
- Explain H1/M15/M5 support and opposition separately for each zone.
- If no zone is currently confirming, say NO_ACTIVE_SETUP even when future BUY/SELL locations are mapped.
- inducement is only a POSSIBLE label when a clear minor internal swing sits between current price and a more important external liquidity/HTF objective. If uncertain say NONE.
- Keep the final zone map uncluttered: these concepts improve zone selection/confirmation, not the number of zones shown.

V23 MULTI-CANDIDATE + ZONE-STRENGTH RULES:
- Do NOT stop at the first plausible support/resistance. deterministic candidate_zones may contain several BUY areas below price and SELL areas above price. Compare them before selecting the displayed primary zone.
- Prefer the strongest confluence cluster, not simply the nearest zone. A nearby internal M5 area can be weaker than a deeper M15/H1 demand area.
- If a meaningful deeper same-side candidate exists, mention it in confluence_summary as a secondary/deeper candidate; never imply price must reach it.
- Repeated touches degrade a zone. Use touch_count, consumption_score and acceptance state. A fourth/fifth test must not score like a fresh first test.
- Separate ZONE QUALITY from CURRENT REACTION QUALITY. A strong historical zone can have weak current confirmation.
- If a BUY zone gets repeated body acceptance deeper into/below it while M5 pressure is bearish, downgrade it aggressively. Reverse for SELL.
- A small wick bounce is REACTION only. CURRENT_CONFIRMATION requires follow-through plus a closed-candle local structure shift; if price returns and loses the reaction extreme, mark REACTION_FAILED / CONSUMED as appropriate.
- Liquidity beyond a candidate zone is opposing context: if material sell-side liquidity sits below a BUY area, do not assume the first support is the final destination. Reverse for SELL.
- Never move a zone lower/higher merely because a previous zone failed. Candidate selection must be based on information available in the supplied screenshot/OHLC, not hindsight.

Return JSON only:
{
 "current_price": null,
 "current_pressure":"BULLISH|BEARISH|NEUTRAL|EXTREME_BULLISH|EXTREME_BEARISH|UNCLEAR",
 "market_phase":"TRENDING|PULLBACK|RANGING|BREAKOUT|REVERSAL_DEVELOPING|EVENT_SHOCK|UNCLEAR",
 "shock_detector":"NORMAL|ELEVATED|TRIGGERED",
 "shock_reason":"short reason",
 "approach_speed":"SLOW|NORMAL|FAST|EXTREME|UNCLEAR",
 "data_ai_conflict":"NONE|MINOR|MAJOR|UNKNOWN",
 "data_ai_conflict_reason":"short reason",
 "htf_refresh_needed":false,
 "htf_refresh_reason":"short reason",
 "m5_state":"BULLISH|BEARISH|UNCLEAR",
 "structure":"HH_HL|LL_LH|MIXED|UNCLEAR",
 "structure_event":"BULLISH_BOS|BEARISH_BOS|BULLISH_CHOCH|BEARISH_CHOCH|NONE|UNCLEAR",
 "volatility":"LOW|NORMAL|HIGH|EXTREME",
 "momentum":"BULLISH_STRONG|BULLISH|NEUTRAL|BEARISH|BEARISH_STRONG|UNCLEAR",
 "m5_description":"short factual description",
 "buy_pullback":{"zone":null,"freshness":"FRESH|NONE","zone_lifecycle":"FRESH|TESTING|REACTED|RETESTED|CONSUMED|INVALIDATED|EXPIRED|NONE","score":0,"score_components":{"freshness":0,"move_away":0,"structure":0,"touches":0,"proximity":0,"invalidation":0,"momentum":0,"data_agreement":0},"quality":"WEAK|MODERATE|STRONG|VERY_STRONG|NONE","reason":"","confirmation_state":"NO_ZONE|WAIT|TESTING|REJECTION_DETECTED|CONFIRMATION_DEVELOPING|CURRENT_CONFIRMATION|HISTORICAL_REACTION|INVALIDATED","confirmation":"","invalidation":""},
 "sell_pullback":{"zone":null,"freshness":"FRESH|NONE","zone_lifecycle":"FRESH|TESTING|REACTED|RETESTED|CONSUMED|INVALIDATED|EXPIRED|NONE","score":0,"score_components":{"freshness":0,"move_away":0,"structure":0,"touches":0,"proximity":0,"invalidation":0,"momentum":0,"data_agreement":0},"quality":"WEAK|MODERATE|STRONG|VERY_STRONG|NONE","reason":"","confirmation_state":"NO_ZONE|WAIT|TESTING|REJECTION_DETECTED|CONFIRMATION_DEVELOPING|CURRENT_CONFIRMATION|HISTORICAL_REACTION|INVALIDATED","confirmation":"","invalidation":""},
 "confluence_summary":"short sequence-based summary including supporting and opposing evidence",
 "order_block_context":"short factual note or none",
 "fvg_quality_context":"short factual note or none",
 "premium_discount_context":"PREMIUM|EQUILIBRIUM|DISCOUNT|UNCLEAR plus short note",
 "liquidity_sweep_context":"short factual note or none",
 "inducement_context":"possible minor inducement level or NONE",
 "session_liquidity_context":"short factual note or none",
 "body_acceptance_context":"short factual note or none",
 "liquidity_context":"short factual note or none",
 "break_retest_context":"short factual note or none",
 "role_flip_context":"short factual note or none",
 "fake_break_context":"short factual note or none",
 "imbalance_context":"short factual note or none",
 "session_context":"short factual note",
 "setup_conflict":"NONE|BULLISH_STRUCTURE_VS_RESISTANCE|BEARISH_STRUCTURE_VS_SUPPORT|MIXED_SIGNALS",
 "too_late":false,
 "too_late_reason":"short reason or none",
 "risk_filter":"PASS|CAUTION|BLOCK",
 "risk_reason":"short reason",
 "action_state":"WAIT|OBSERVE_REACTION|CURRENT_CONFIRMATION_PRESENT|NO_VALID_SETUP|HIGH_RISK_EVENT|VOLATILITY_PAUSE",
 "note":"Analysis aid only; confirmation is not certainty."
}
'''

HTF_PROMPT = r'''
You are Gold Scanner V22 higher-timeframe context extractor. You receive ONE XAUUSD chart screenshot whose timeframe is explicitly H1 or M15. Extract compact context for later M5 analysis. Do not give entries, trade directions, targets, or predictions. Newest/right-edge candles matter most.
V18 MULTI-TIMEFRAME ARCHITECTURE:
- multi_timeframe_metrics contains deterministic M5, M15 and H1 calculations from deeper OHLC history when LIVE/PARTIAL data is available. Use it even if screenshot zoom hides older structure.
- H1 = broad context and major zones; M15 = intermediate context; M5 = execution. Higher timeframes add evidence but never automatically force direction.
- Evaluate BUY CASE and SELL CASE independently on every scan. A bullish H1 recovery must not suppress a valid developing M15/M5 sell case, and vice versa. Output BUY only, SELL only, BOTH, or neither based on evidence.
- Distinguish long-term trend, current recovery/pullback, and newest execution momentum. Do not label a recovery as a full structural reversal unless structure evidence supports it.
- Prefer exact OHLC highs/lows for structure and zone boundaries when data exists; use Gemini screenshot vision as visual second opinion.
- If screenshot interpretation conflicts with deterministic data, set setup_conflict=MIXED_SIGNALS and be conservative.
- Use only CLOSED-candle structure evidence from deterministic metrics; do not call an intrabar wick a BOS/CHoCH.
- H1 and M15 screenshots are preferably LANDSCAPE to maximize broad historical context. The fresh M5 screenshot is preferably PORTRAIT so newest execution candles, wicks, rejection and local structure are larger and easier to inspect. Do not penalize other orientations; deep OHLC data should reduce dependence on screenshot field-of-view.
- Saved H1/M15 screenshot context is supplementary. If live higher-timeframe OHLC materially conflicts with saved screenshot context, reduce reliance on saved context and request refresh in m5_description, but still complete the M5 analysis.

Return JSON only:
{
 "timeframe":"H1|M15",
 "state":"BULLISH|BEARISH|RANGE|UNCLEAR",
 "structure":"HH_HL|LL_LH|MIXED|UNCLEAR",
 "structure_event":"BULLISH_BOS|BEARISH_BOS|BULLISH_CHOCH|BEARISH_CHOCH|NONE|UNCLEAR",
 "major_support":[{"low":0,"high":0,"reason":""}],
 "major_resistance":[{"low":0,"high":0,"reason":""}],
 "important_swing_highs":[0],
 "important_swing_lows":[0],
 "range_high":null,
 "range_low":null,
 "context_summary":"short factual summary",
 "refresh_if":"specific structural condition that would make this screenshot context stale"
}
Keep at most 3 support and 3 resistance zones. Use null/empty arrays when unreadable.
'''

def image_part(data_url):
    header, body = data_url.split(',', 1)
    mime = header.split(';', 1)[0].replace('data:', '')
    return types.Part.from_bytes(data=base64.b64decode(body), mime_type=mime)

def fetch_tf(interval, outputsize):
    key=os.environ.get('TWELVE_DATA_API_KEY','').strip()
    if not key: return None, 'SCREENSHOT_ONLY', 'TWELVE_DATA_API_KEY not configured'
    q=urllib.parse.urlencode({'symbol':'XAU/USD','interval':interval,'outputsize':outputsize,'timezone':'UTC','apikey':key})
    try:
        with urllib.request.urlopen('https://api.twelvedata.com/time_series?'+q, timeout=8) as resp:
            d=json.loads(resp.read().decode())
        vals=d.get('values') or []
        if d.get('status')=='error' or len(vals)<25: return None,'DATA_UNAVAILABLE',d.get('message','Not enough candles')
        candles=[{'t':v['datetime'],'o':float(v['open']),'h':float(v['high']),'l':float(v['low']),'c':float(v['close'])} for v in reversed(vals)]
        return candles,'LIVE_DATA',f'Twelve Data XAU/USD {interval}'
    except Exception as e:
        return None,'DATA_UNAVAILABLE',str(e)[:220]

def fetch_multitimeframe():
    specs={'M5':('5min',240),'M15':('15min',240),'H1':('1h',240)}
    out={}; statuses=[]; notes=[]
    for tf,(interval,n) in specs.items():
        c,st,note=fetch_tf(interval,n); out[tf]={'candles':c,'status':st,'note':note,'metrics':analytics(c) if c else {}}; statuses.append(st); notes.append(tf+': '+note)
    overall='LIVE_DATA' if all(x=='LIVE_DATA' for x in statuses) else 'PARTIAL_DATA' if any(x=='LIVE_DATA' for x in statuses) else statuses[0] if statuses else 'DATA_UNAVAILABLE'
    return out,overall,' | '.join(notes)

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
    # V16 deterministic context: displacement, FVGs, session and extension/chase context.
    avg20=sum(abs(x['c']-x['o']) for x in c[-20:])/min(20,len(c))
    displacement='NONE'
    if avg20>0 and abs(last['c']-last['o']) >= 1.8*avg20:
        displacement='BULLISH' if last['c']>last['o'] else 'BEARISH'
    fvgs=[]
    for i in range(max(2,len(c)-30),len(c)):
        a,b=c[i-2],c[i]
        if b['l']>a['h']: fvgs.append({'type':'BULLISH_FVG','low':round(a['h'],2),'high':round(b['l'],2),'age_bars':len(c)-1-i})
        elif b['h']<a['l']: fvgs.append({'type':'BEARISH_FVG','low':round(b['h'],2),'high':round(a['l'],2),'age_bars':len(c)-1-i})
    try:
        hour=int(str(last['t']).split(' ')[1].split(':')[0])
    except: hour=0
    session='ASIA' if hour<7 else 'LONDON' if hour<12 else 'LONDON_NEW_YORK_OVERLAP' if hour<16 else 'NEW_YORK' if hour<21 else 'OFF_HOURS'
    extension_atr=round(abs(move)/(atr or 1),2)
    chase_risk='HIGH' if extension_atr>=2.0 else 'CAUTION' if extension_atr>=1.25 else 'NORMAL'
    # V19 deterministic protection: pressure, phase, shock and approach speed.
    last_range=last['h']-last['l']; range_atr=last_range/(atr or 1); body_atr=abs(last['c']-last['o'])/(atr or 1)
    last3_move=last['c']-(c[-4]['c'] if len(c)>=4 else c[0]['c']); move3_atr=abs(last3_move)/(atr or 1)
    shock='TRIGGERED' if (range_atr>=2.4 or move3_atr>=3.0) else 'ELEVATED' if (range_atr>=1.6 or move3_atr>=2.0 or vol=='EXTREME') else 'NORMAL'
    pressure='EXTREME_BULLISH' if last3_move>0 and shock=='TRIGGERED' else 'EXTREME_BEARISH' if last3_move<0 and shock=='TRIGGERED' else 'BULLISH' if last3_move>0.35*(atr or 1) else 'BEARISH' if last3_move<-0.35*(atr or 1) else 'NEUTRAL'
    if shock=='TRIGGERED': phase='EVENT_SHOCK'
    elif event in ('BULLISH_BOS','BEARISH_BOS') and vol in ('HIGH','EXTREME'): phase='BREAKOUT'
    elif structure in ('HH_HL','LL_LH') and mom not in ('NEUTRAL','UNCLEAR'): phase='TRENDING'
    elif structure=='MIXED' and vol in ('LOW','NORMAL'): phase='RANGING'
    elif event in ('BULLISH_CHOCH','BEARISH_CHOCH'): phase='REVERSAL_DEVELOPING'
    else: phase='PULLBACK' if mom not in ('NEUTRAL','UNCLEAR') else 'UNCLEAR'
    speed='EXTREME' if move3_atr>=2.5 else 'FAST' if move3_atr>=1.4 else 'SLOW' if move3_atr<0.45 else 'NORMAL'
    
    # V20 closed-candle/reaction diagnostics. Twelve Data series is treated as closed-candle input by the engine.
    recent=c[-6:]
    bull=sum(1 for x in recent if x['c']>x['o']); bear=sum(1 for x in recent if x['c']<x['o'])
    wick_reject='LOWER' if (last['c']-last['l']) > 1.4*abs(last['c']-last['o']) else 'UPPER' if (last['h']-last['c']) > 1.4*abs(last['c']-last['o']) else 'NONE'
    reaction_quality='STRONG' if abs(move3_atr)>=1.8 and max(bull,bear)>=4 else 'MODERATE' if abs(move3_atr)>=0.8 and max(bull,bear)>=3 else 'WEAK'

    # V21 price-action confluence engine. These are deterministic evidence features, not trade signals.
    # FVG quality: freshness/fill state + displacement alignment.
    quality_fvgs=[]
    for g in fvgs[-8:]:
        lo,hi=g['low'],g['high']; age=g['age_bars']; created_idx=max(0,len(c)-1-age)
        after=c[created_idx+1:] if created_idx+1<len(c) else []
        touched=any(x['l']<=hi and x['h']>=lo for x in after)
        fully=any(x['l']<=lo and x['h']>=hi for x in after)
        state='FILLED' if fully else 'PARTIAL_OR_TOUCHED' if touched else 'FRESH'
        aligned=(g['type']=='BULLISH_FVG' and displacement=='BULLISH') or (g['type']=='BEARISH_FVG' and displacement=='BEARISH')
        q='HIGH' if state=='FRESH' and aligned and age<=12 else 'MEDIUM' if state!='FILLED' and age<=24 else 'LOW'
        quality_fvgs.append({**g,'fill_state':state,'quality':q})

    # Order-block heuristic: last opposite candle before a >=1.5 ATR 3-candle displacement.
    order_blocks=[]
    start=max(3,len(c)-45)
    for i in range(start,len(c)-2):
        end=c[i+2]; move_seq=end['c']-c[i]['o']
        if abs(move_seq) < 1.5*(atr or 1): continue
        direction_ob='BULLISH_OB' if move_seq>0 else 'BEARISH_OB'
        for j in range(i-1,max(-1,i-5),-1):
            x=c[j]; opposite=(direction_ob=='BULLISH_OB' and x['c']<x['o']) or (direction_ob=='BEARISH_OB' and x['c']>x['o'])
            if opposite:
                lo=min(x['o'],x['c'],x['l']); hi=max(x['o'],x['c'],x['h'])
                later=c[j+1:]
                invalid=any(y['c']<lo for y in later) if direction_ob=='BULLISH_OB' else any(y['c']>hi for y in later)
                touches=sum(1 for y in later if y['l']<=hi and y['h']>=lo)
                state='BREAKER' if invalid else 'FRESH' if touches<=1 else 'MITIGATED'
                order_blocks.append({'type':direction_ob,'low':round(lo,2),'high':round(hi,2),'state':state,'touches':touches,'age_bars':len(c)-1-j})
                break
    # Deduplicate nearby blocks and keep recent ones.
    obs=[]
    for ob in reversed(order_blocks):
        if not any(x['type']==ob['type'] and abs(x['low']-ob['low'])<=max(.2,atr*.12) for x in obs): obs.append(ob)
        if len(obs)>=4: break
    obs=list(reversed(obs))

    # Premium/discount from latest meaningful swing range.
    range_hi=swings_hi[-1][1] if swings_hi else max(x['h'] for x in c[-40:])
    range_lo=swings_lo[-1][1] if swings_lo else min(x['l'] for x in c[-40:])
    if range_hi<=range_lo:
        range_hi=max(x['h'] for x in c[-40:]); range_lo=min(x['l'] for x in c[-40:])
    equilibrium=(range_hi+range_lo)/2
    pd='PREMIUM' if last['c']>equilibrium+0.1*(range_hi-range_lo) else 'DISCOUNT' if last['c']<equilibrium-0.1*(range_hi-range_lo) else 'EQUILIBRIUM'

    # External liquidity = latest major swing extremes; internal liquidity = equal levels / minor recent swings inside range.
    external_liq={'above':round(range_hi,2),'below':round(range_lo,2)}
    internal_liq={'equal_highs':eqh[-2:],'equal_lows':eql[-2:],'minor_highs':[round(x[1],2) for x in swings_hi[-3:-1]],'minor_lows':[round(x[1],2) for x in swings_lo[-3:-1]]}

    # Sweep/reclaim classification on closed candles.
    sweep='NONE'
    if len(c)>=3:
        prior_h=max(x['h'] for x in c[-12:-1]); prior_l=min(x['l'] for x in c[-12:-1])
        if last['h']>prior_h and last['c']<prior_h: sweep='BUY_SIDE_SWEEP_RECLAIM_DOWN'
        elif last['l']<prior_l and last['c']>prior_l: sweep='SELL_SIDE_SWEEP_RECLAIM_UP'

    # Candle-body acceptance versus wick rejection around the latest swing boundary.
    acceptance='NONE'
    if swings_hi and sum(1 for x in c[-3:] if x['c']>swings_hi[-1][1])>=2: acceptance='ACCEPTED_ABOVE_SWING'
    elif swings_lo and sum(1 for x in c[-3:] if x['c']<swings_lo[-1][1])>=2: acceptance='ACCEPTED_BELOW_SWING'
    elif sweep!='NONE': acceptance='WICK_SWEEP_RECLAIM'

    # Session liquidity and simple opening ranges from the latest UTC date in the feed.
    def hour_of(x):
        try:return int(str(x['t']).split(' ')[1].split(':')[0])
        except:return None
    latest_day=str(last['t']).split(' ')[0]
    day=[x for x in c if str(x['t']).startswith(latest_day)]
    def window(a,b):
        xs=[x for x in day if hour_of(x) is not None and a<=hour_of(x)<b]
        return {'high':round(max(x['h'] for x in xs),2),'low':round(min(x['l'] for x in xs),2)} if xs else None
    session_liq={'asia':window(0,7),'london':window(7,12),'new_york':window(12,21),'london_opening_range':window(7,8),'ny_opening_range':window(12,13)}

    # Sequence recognition: sweep -> displacement/structure event -> nearby FVG.
    sequence='NONE'
    recent_high_q=any(g['type']=='BULLISH_FVG' and g.get('quality') in ('HIGH','MEDIUM') for g in quality_fvgs[-4:])
    recent_low_q=any(g['type']=='BEARISH_FVG' and g.get('quality') in ('HIGH','MEDIUM') for g in quality_fvgs[-4:])
    if sweep=='SELL_SIDE_SWEEP_RECLAIM_UP' and event in ('BULLISH_BOS','BULLISH_CHOCH') and recent_high_q: sequence='BULLISH_SWEEP_STRUCTURE_FVG'
    elif sweep=='BUY_SIDE_SWEEP_RECLAIM_DOWN' and event in ('BEARISH_BOS','BEARISH_CHOCH') and recent_low_q: sequence='BEARISH_SWEEP_STRUCTURE_FVG'
    elif event in ('BULLISH_BOS','BULLISH_CHOCH') and recent_high_q: sequence='BULLISH_STRUCTURE_FVG'
    elif event in ('BEARISH_BOS','BEARISH_CHOCH') and recent_low_q: sequence='BEARISH_STRUCTURE_FVG'

    # Confluence clustering: transparent evidence count, not probability.
    bull_factors=[]; bear_factors=[]
    if structure=='HH_HL': bull_factors.append('HH/HL structure')
    if structure=='LL_LH': bear_factors.append('LL/LH structure')
    if event in ('BULLISH_BOS','BULLISH_CHOCH'): bull_factors.append(event)
    if event in ('BEARISH_BOS','BEARISH_CHOCH'): bear_factors.append(event)
    if mom.startswith('BULLISH'): bull_factors.append('bullish momentum')
    if mom.startswith('BEARISH'): bear_factors.append('bearish momentum')
    if sweep=='SELL_SIDE_SWEEP_RECLAIM_UP': bull_factors.append('sell-side sweep/reclaim')
    if sweep=='BUY_SIDE_SWEEP_RECLAIM_DOWN': bear_factors.append('buy-side sweep/reclaim')
    if any(g['type']=='BULLISH_FVG' and g['quality']=='HIGH' for g in quality_fvgs): bull_factors.append('high-quality bullish FVG')
    if any(g['type']=='BEARISH_FVG' and g['quality']=='HIGH' for g in quality_fvgs): bear_factors.append('high-quality bearish FVG')
    if any(o['type']=='BULLISH_OB' and o['state']!='BREAKER' for o in obs): bull_factors.append('active bullish order block')
    if any(o['type']=='BEARISH_OB' and o['state']!='BREAKER' for o in obs): bear_factors.append('active bearish order block')
    if pd=='DISCOUNT': bull_factors.append('discount location')
    if pd=='PREMIUM': bear_factors.append('premium location')
    confluence={'bullish':bull_factors,'bearish':bear_factors,'bullish_count':len(bull_factors),'bearish_count':len(bear_factors),'sequence':sequence}

    # V23 multi-candidate zone map. Deterministic candidates are ranked evidence locations, not signals.
    cp=last['c']; candidates=[]; ztol=max(atr*0.18,0.25)
    def add_candidate(side,lo,hi,kind,base,meta=None):
        lo,hi=float(min(lo,hi)),float(max(lo,hi))
        if side=='BUY' and hi>=cp: return
        if side=='SELL' and lo<=cp: return
        # Count recent interactions; repeated tests increase consumption.
        recent60=c[-60:]; touches=sum(1 for x in recent60 if x['l']<=hi and x['h']>=lo)
        bodies=sum(1 for x in recent60[-8:] if (side=='BUY' and x['c']<hi) or (side=='SELL' and x['c']>lo))
        distance=(cp-hi) if side=='BUY' else (lo-cp)
        score=base - min(24,max(0,touches-1)*6) - min(12,bodies*2) - min(12,int((distance/(atr or 1))*2))
        score=max(0,min(100,int(score)))
        consumption='HEAVY' if touches>=5 or bodies>=4 else 'MODERATE' if touches>=3 or bodies>=2 else 'LIGHT' if touches>=1 else 'UNTOUCHED'
        candidates.append({'side':side,'low':round(lo,2),'high':round(hi,2),'source':kind,'rank_score':score,'touch_count':touches,'body_penetration_count':bodies,'consumption':consumption,'distance_atr':round(distance/(atr or 1),2),'meta':meta or {}})
    for o in obs:
        if o['state']=='BREAKER': continue
        add_candidate('BUY' if o['type']=='BULLISH_OB' else 'SELL',o['low'],o['high'],o['type'],78 if o['state']=='FRESH' else 66,{'state':o['state']})
    for g in quality_fvgs:
        if g.get('fill_state')=='FILLED': continue
        add_candidate('BUY' if g['type']=='BULLISH_FVG' else 'SELL',g['low'],g['high'],g['type'],72 if g.get('quality')=='HIGH' else 60,{'quality':g.get('quality'),'fill_state':g.get('fill_state')})
    for _,v in swings_lo[-5:]: add_candidate('BUY',v-ztol,v+ztol,'SWING_DEMAND',62)
    for _,v in swings_hi[-5:]: add_candidate('SELL',v-ztol,v+ztol,'SWING_SUPPLY',62)
    # Deduplicate overlapping same-side candidates, preserving the stronger one.
    ranked=[]
    for q in sorted(candidates,key=lambda x:x['rank_score'],reverse=True):
        if not any(r['side']==q['side'] and not (q['high']<r['low']-ztol or q['low']>r['high']+ztol) for r in ranked): ranked.append(q)
    candidate_zones={'buy':[x for x in ranked if x['side']=='BUY'][:4],'sell':[x for x in ranked if x['side']=='SELL'][:4]}

    return {'closed_candle_engine':True,'reaction_quality':reaction_quality,'latest_wick_rejection':wick_reject,'recent_bull_candles':bull,'recent_bear_candles':bear,'data_current_price':round(last['c'],3),'atr14':round(atr,3),'structure':structure,'structure_event':event,'momentum':mom,'volatility':vol,'current_pressure':pressure,'market_phase':phase,'shock_detector':shock,'last_candle_range_atr':round(range_atr,2),'last_candle_body_atr':round(body_atr,2),'approach_speed':speed,'move_3bar_atr':round(move3_atr,2),'last_swing_highs':[round(x[1],2) for x in swings_hi[-3:]],'last_swing_lows':[round(x[1],2) for x in swings_lo[-3:]],'equal_highs':eqh[-2:],'equal_lows':eql[-2:],'recent_5bar_move':round(move,3),'avg_body_5':round(avg_body,3),'displacement':displacement,'recent_fvgs':fvgs[-4:],'session_utc':session,'extension_atr_5bar':extension_atr,'chase_risk':chase_risk,'fvg_quality':quality_fvgs[-6:],'order_blocks':obs,'premium_discount':{'state':pd,'range_low':round(range_lo,2),'equilibrium':round(equilibrium,2),'range_high':round(range_hi,2)},'external_liquidity':external_liq,'internal_liquidity':internal_liq,'liquidity_sweep':sweep,'body_acceptance':acceptance,'session_liquidity':session_liq,'price_action_sequence':sequence,'confluence_cluster':confluence,'candidate_zones':candidate_zones,'latest_closed_candles':c[-12:]}

def run_model(contents):
    client=genai.Client(api_key=os.environ['GEMINI_API_KEY'])
    model=os.environ.get('GEMINI_MODEL','gemini-3.6-flash')
    response=client.models.generate_content(model=model,contents=contents,config=types.GenerateContentConfig(response_mime_type='application/json',temperature=0.02))
    r=json.loads(response.text); r['model_used']=model; return r

def clamp(v):
    try:return max(0,min(100,int(round(float(v)))))
    except:return 0

def qual(s): return 'NONE' if s<=0 else 'WEAK' if s<50 else 'MODERATE' if s<70 else 'STRONG' if s<85 else 'VERY_STRONG'

def zone_bounds(zone):
    import re
    if not zone: return None
    nums=[float(x) for x in re.findall(r'\d+(?:\.\d+)?',str(zone))]
    if len(nums)<2:return None
    return min(nums[0],nums[1]),max(nums[0],nums[1])

def reconcile_zone_lifecycle(z,side,metrics,current_price):
    """V23: closed-candle lifecycle with approach-aware touches and consumption."""
    bounds=zone_bounds(z.get('zone')); candles=(metrics.get('latest_closed_candles') or [])[-12:]
    if not bounds or len(candles)<2:return z
    lo,hi=bounds; atr=float(metrics.get('atr14') or max((hi-lo),1.0)); cp=float(current_price) if current_price is not None else float(candles[-1]['c'])
    dist=0.0 if lo<=cp<=hi else (lo-cp if cp<lo else cp-hi); z['distance_to_zone']=round(dist,3); z['distance_atr']=round(dist/atr,2) if atr else None
    # Only start lifecycle after a genuine approach from the correct side. This avoids treating old pre-zone candles as invalidation.
    approach=None
    for i in range(1,len(candles)):
        prev=float(candles[i-1]['c']); x=candles[i]
        if side=='buy' and prev>hi and float(x['l'])<=hi: approach=i; break
        if side=='sell' and prev<lo and float(x['h'])>=lo: approach=i; break
    if approach is None:
        z['zone_lifecycle']='FRESH'; z['freshness']='FRESH'; z['timing_status']='UNTESTED'; z['timing_note']='No completed-candle approach into this zone was found in the recent OHLC window.'; z['touch_count']=0; z['consumption_score']=0; z['reaction_quality_current']='NONE'; return z
    after=candles[approach:]; touches=sum(1 for x in after if float(x['l'])<=hi and float(x['h'])>=lo)
    body_deep=sum(1 for x in after if (side=='buy' and float(x['c'])<(lo+hi)/2) or (side=='sell' and float(x['c'])>(lo+hi)/2))
    invalid=[x for x in after if (side=='buy' and float(x['c'])<lo) or (side=='sell' and float(x['c'])>hi)]
    consumption=min(100,max(0,(touches-1)*18 + body_deep*12)); z['touch_count']=touches; z['consumption_score']=consumption
    # Reaction is measured from zone to best favorable close after approach.
    favorable=max(float(x['c'])-hi for x in after) if side=='buy' else max(lo-float(x['c']) for x in after)
    rq='STRONG' if favorable>=0.8*atr else 'MODERATE' if favorable>=0.4*atr else 'WEAK' if favorable>0 else 'NONE'; z['reaction_quality_current']=rq
    if invalid:
        z['zone_lifecycle']='INVALIDATED'; z['freshness']='USED'; z['confirmation_state']='INVALIDATED'; z['timing_status']='INVALIDATED'; z['timing_note']=f'Closed M5 acceptance beyond the zone occurred after approach. Touches: {touches}; consumption {consumption}/100.'; return z
    if consumption>=65:
        z['zone_lifecycle']='CONSUMED'; z['freshness']='USED'; z['confirmation_state']='WAIT'; z['timing_status']='ZONE_WEAKENING'; z['timing_note']=f'Repeated interaction/body penetration is consuming this zone. Touches: {touches}; consumption {consumption}/100.'; return z
    at_zone=(lo-0.15*atr)<=cp<=(hi+0.15*atr)
    if at_zone:
        z['zone_lifecycle']='TESTING'; z['freshness']='USED'; z['timing_status']='ACTIVE_TEST'; z['timing_note']=f'Price is testing a used zone. Touches: {touches}; consumption {consumption}/100; reaction quality {rq}.'
    elif favorable>=0.35*atr:
        # If it reacted but then returned close to the zone, flag failed reaction rather than confirmation.
        returned=(side=='buy' and cp<=hi+0.25*atr) or (side=='sell' and cp>=lo-0.25*atr)
        z['zone_lifecycle']='RETESTED' if returned else 'REACTED'; z['freshness']='USED'; z['confirmation_state']='WAIT' if returned else 'HISTORICAL_REACTION'; z['timing_status']='REACTION_FAILED_RETEST' if returned else 'ALREADY_REACTED'; z['timing_note']=f'Initial reaction quality {rq}; '+('price returned toward the zone, so the reaction is not confirmed.' if returned else 'price moved away; this is historical reaction, not a fresh setup.')
    else:
        z['zone_lifecycle']='RETESTED'; z['freshness']='USED'; z['timing_status']='WEAK_REACTION'; z['timing_note']=f'Zone was touched but favorable follow-through was weak. Touches: {touches}; consumption {consumption}/100.'
    return z

def norm(r,metrics,data_status,event_risk):
    if not isinstance(r,dict):r={}
    if data_status=='LIVE_DATA' and metrics.get('data_current_price') is not None:r['current_price']=metrics['data_current_price']
    else:
        try:r['current_price']=float(r.get('current_price')) if r.get('current_price') is not None else None
        except:r['current_price']=None
    for k,allowed,default in [('m5_state',{'BULLISH','BEARISH','UNCLEAR'},'UNCLEAR'),('structure',{'HH_HL','LL_LH','MIXED','UNCLEAR'},'UNCLEAR'),('structure_event',{'BULLISH_BOS','BEARISH_BOS','BULLISH_CHOCH','BEARISH_CHOCH','NONE','UNCLEAR'},'UNCLEAR'),('volatility',{'LOW','NORMAL','HIGH','EXTREME'},'NORMAL'),('momentum',{'BULLISH_STRONG','BULLISH','NEUTRAL','BEARISH','BEARISH_STRONG','UNCLEAR'},'UNCLEAR')]:
        v=str(r.get(k) or default).upper(); r[k]=v if v in allowed else default
    # Deterministic V19 fields override visual guesses when live data exists.
    if data_status=='LIVE_DATA':
        r['current_pressure']=metrics.get('current_pressure','UNCLEAR'); r['market_phase']=metrics.get('market_phase','UNCLEAR'); r['shock_detector']=metrics.get('shock_detector','NORMAL'); r['approach_speed']=metrics.get('approach_speed','UNCLEAR')
    else:
        r.setdefault('current_pressure','UNCLEAR'); r.setdefault('market_phase','UNCLEAR'); r.setdefault('shock_detector','NORMAL'); r.setdefault('approach_speed','UNCLEAR')
    r.setdefault('data_ai_conflict','UNKNOWN'); r.setdefault('data_ai_conflict_reason','')
    r.setdefault('htf_refresh_needed',False); r.setdefault('htf_refresh_reason','')
    valid={'NO_ZONE','WAIT','TESTING','REJECTION_DETECTED','CONFIRMATION_DEVELOPING','CURRENT_CONFIRMATION','HISTORICAL_REACTION','INVALIDATED'}
    cp=r.get('current_price')
    for side in ('buy_pullback','sell_pullback'):
        z=r.get(side) if isinstance(r.get(side),dict) else {}; zone=z.get('zone')
        if not zone:
            r[side]={'zone':None,'freshness':'NONE','zone_lifecycle':'NONE','score':0,'score_components':{},'quality':'NONE','reason':z.get('reason') or 'No clear zone.','confirmation_state':'NO_ZONE','confirmation':'','invalidation':'','timing_status':'NO_ZONE','timing_note':'','distance_to_zone':None,'distance_atr':None};continue
        s=clamp(z.get('score')); st=str(z.get('confirmation_state') or 'WAIT').upper(); st=st if st in valid else 'WAIT'
        conf=(z.get('confirmation') or '').lower()
        if st=='CURRENT_CONFIRMATION' and not any(w in conf for w in ('current','newest','retest','testing','now','latest')): st='HISTORICAL_REACTION'
        z.update({'score':s,'quality':qual(s),'confirmation_state':st}); z.setdefault('score_components',{})
        for k in ('reason','confirmation','invalidation'):z.setdefault(k,'')
        if data_status=='LIVE_DATA': z=reconcile_zone_lifecycle(z,'buy' if side=='buy_pullback' else 'sell',metrics,cp)
        else:
            life=str(z.get('zone_lifecycle') or 'FRESH').upper(); z['zone_lifecycle']=life if life in {'FRESH','TESTING','REACTED','RETESTED','CONSUMED','INVALIDATED','EXPIRED'} else 'FRESH'; z.setdefault('timing_status','VISUAL_ONLY'); z.setdefault('timing_note','Lifecycle is based on screenshot analysis because live OHLC is unavailable.'); z.setdefault('distance_to_zone',None); z.setdefault('distance_atr',None)
        r[side]=z
    # V22 active-setup summary separates mapped locations from what is actionable now.
    active=[]
    for name,side in [('BUY','buy_pullback'),('SELL','sell_pullback')]:
        z=r[side]
        if z.get('confirmation_state') in {'CURRENT_CONFIRMATION','CONFIRMATION_DEVELOPING','REJECTION_DETECTED'} and z.get('zone_lifecycle') not in {'REACTED','CONSUMED','INVALIDATED','EXPIRED'}: active.append(name)
    r['active_setup']=' + '.join(active) if active else 'NO_ACTIVE_SETUP'
    r['candidate_zones']=metrics.get('candidate_zones',{}) if data_status=='LIVE_DATA' else {}
    r['timing_summary']='Mapped zones are locations to monitor. V23 compares multiple candidates, consumption and reaction quality before treating a zone as strong.'
    act=str(r.get('action_state') or 'WAIT').upper(); allowed={'WAIT','OBSERVE_REACTION','CURRENT_CONFIRMATION_PRESENT','NO_VALID_SETUP','HIGH_RISK_EVENT','VOLATILITY_PAUSE'}
    if act not in allowed:act='WAIT'
    if bool(r.get('too_late')): act='NO_VALID_SETUP'; r['risk_filter']='BLOCK'; r['risk_reason']=r.get('too_late_reason') or 'Move is already extended; chase filter blocked the setup.'
    if event_risk=='HIGH':act='HIGH_RISK_EVENT';r['risk_filter']='BLOCK';r['risk_reason']='High-impact news/event mode is enabled; technical confirmation can be unstable.'
    elif metrics.get('shock_detector')=='TRIGGERED':
        act='VOLATILITY_PAUSE'; r['risk_filter']='BLOCK'; r['risk_reason']='V23 volatility-shock detector triggered from closed-candle OHLC; normal zone logic is paused until structure stabilizes.'; r['htf_refresh_needed']=True; r['htf_refresh_reason']=r.get('htf_refresh_reason') or 'Extreme M5 displacement can make saved H1/M15 visual context stale; refresh after volatility settles.'
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

@app.post('/api/context')
def context_scan():
    try:
        d=request.get_json(force=True)
        tf=str(d.get('timeframe') or '').upper()
        img=d.get('image')
        if tf not in {'H1','M15'} or not img:
            return jsonify({'error':'missing_context','detail':'H1 or M15 screenshot and timeframe are required.'}),400
        result=run_model([HTF_PROMPT, 'TIMEFRAME: '+tf, image_part(img)])
        result['timeframe']=tf
        result['saved_at']=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()
        result['refresh_after_minutes']=180 if tf=='H1' else 45
        return jsonify(result)
    except Exception as e:
        text=str(e); low=text.lower(); quota=('429' in text or 'resource_exhausted' in low or 'quota' in low)
        return jsonify({'error':'quota' if quota else 'context_failed','detail':text[:1200]}),429 if quota else 500

@app.get('/api/ohlc-test')
def ohlc_test():
    """Quota-free Twelve Data connectivity + deterministic HTF engine test."""
    try:
        mtf,status,note=fetch_multitimeframe()
        details={}
        for tf,v in mtf.items():
            c=v.get('candles') or []; m=v.get('metrics') or {}
            details[tf]={
                'status':v.get('status'),'candles_received':len(c),'latest_time':c[-1]['t'] if c else None,
                'latest_close':c[-1]['c'] if c else None,'structure':m.get('structure'),'structure_event':m.get('structure_event'),
                'momentum':m.get('momentum'),'atr14':m.get('atr14'),'candidate_zones':m.get('candidate_zones',{})
            }
        return jsonify({'status':status,'gemini_used':False,'symbol':'XAU/USD','timeframes':details,'note':note})
    except Exception as e:return jsonify({'error':'ohlc_test_failed','detail':str(e)[:900]}),500

def data_only_result(mtf,data_status,data_note,why='Gemini visual check unavailable'):
    m5=mtf.get('M5',{}).get('metrics',{}); m15=mtf.get('M15',{}).get('metrics',{}); h1=mtf.get('H1',{}).get('metrics',{})
    def top(side):
        arr=(m5.get('candidate_zones') or {}).get(side,[])
        return arr[0] if arr else None
    return {
      'mode':'DATA_ONLY','data_status':data_status,'data_note':data_note,'gemini_status':why,
      'current_price':m5.get('data_current_price'),'current_pressure':m5.get('current_pressure','UNCLEAR'),
      'market_phase':m5.get('market_phase','UNCLEAR'),'shock_detector':m5.get('shock_detector','NORMAL'),
      'approach_speed':m5.get('approach_speed','UNCLEAR'),'m5_state':'BULLISH' if str(m5.get('momentum','')).startswith('BULLISH') else 'BEARISH' if str(m5.get('momentum','')).startswith('BEARISH') else 'UNCLEAR',
      'structure':m5.get('structure','UNCLEAR'),'structure_event':m5.get('structure_event','NONE'),'volatility':m5.get('volatility','NORMAL'),'momentum':m5.get('momentum','UNCLEAR'),
      'multi_timeframe_metrics':{'H1':h1,'M15':m15,'M5':m5},'candidate_zones':m5.get('candidate_zones',{}),
      'data_only_summary':f"H1 {h1.get('structure','—')} · M15 {m15.get('structure','—')} · M5 {m5.get('structure','—')}. Exact OHLC engine active; Gemini visual confirmation unavailable.",
      'buy_candidate':top('buy'),'sell_candidate':top('sell'),
      'note':'Data-only analysis aid. Candidate zones and structure are deterministic evidence, not guaranteed reversal points.'
    }

@app.post('/api/scan')
def scan():
    try:
        d=request.get_json(force=True)
        if not d.get('m5'):return jsonify({'error':'missing_image','detail':'One fresh M5 screenshot is required for hybrid mode.'}),400
        event_risk='HIGH' if d.get('event_risk') else 'NORMAL'
        mtf,data_status,data_note=fetch_multitimeframe(); metrics=mtf.get('M5',{}).get('metrics',{})
        mtf_metrics={tf:v.get('metrics',{}) for tf,v in mtf.items()}
        context={'data_status':data_status,'data_note':data_note,'deterministic_metrics':metrics,'multi_timeframe_metrics':mtf_metrics,'event_risk':event_risk,'risk_budget':d.get('risk_budget'),'spread_cost':d.get('spread_cost'),'broker_specs':d.get('broker_specs'),'setup_memory':d.get('setup_memory'),'automatic_event_status':'UNKNOWN_NO_CALENDAR_FEED','input_guidance':'H1/M15/M5 are fetched automatically from OHLC. The user supplies only one fresh M5 screenshot. Evaluate BUY and SELL cases independently; H1/M15 are context, M5 is execution.'}
        try:
            result=run_model([PROMPT,'SERVER CONTEXT JSON:\n'+json.dumps(context,separators=(',',':')),image_part(d['m5'])])
            out=norm(result,metrics,data_status,event_risk); out['multi_timeframe_metrics']=mtf_metrics; out['mode']='HYBRID_OHLC_VISUAL'; out['gemini_status']='AVAILABLE'; return jsonify(out)
        except Exception as ge:
            text=str(ge); low=text.lower(); quota=('429' in text or 'resource_exhausted' in low or 'quota' in low)
            if quota and data_status in ('LIVE_DATA','PARTIAL_DATA'):
                return jsonify(data_only_result(mtf,data_status,data_note,'QUOTA_EXHAUSTED'))
            raise
    except Exception as e:
        text=str(e);low=text.lower();quota=('429' in text or 'resource_exhausted' in low or 'quota' in low)
        return jsonify({'error':'quota' if quota else 'scan_failed','detail':text[:1200]}),429 if quota else 500



def parse_zone(zone):
    import re
    if not zone: return None
    nums=[float(x) for x in re.findall(r'\d+(?:\.\d+)?',str(zone))]
    if len(nums)<2:return None
    return (min(nums[0],nums[1]),max(nums[0],nums[1]))

def evaluate_setup(setup,candles):
    """Deterministic journal outcome. This measures zone behavior, not profitability."""
    out={'time':setup.get('time'),'price':setup.get('price'),'buy':'NO_ZONE','sell':'NO_ZONE'}
    if not candles:return out
    for side in ('buy','sell'):
        z=setup.get(side) or {}; bounds=parse_zone(z.get('zone')) if isinstance(z,dict) else None
        if not bounds:continue
        lo,hi=bounds; touched=any(x['l']<=hi and x['h']>=lo for x in candles)
        if not touched:out[side]='NOT_TRIGGERED';continue
        if side=='buy':
            invalid=any(x['c']<lo for x in candles); favorable=max(x['h']-hi for x in candles)
        else:
            invalid=any(x['c']>hi for x in candles); favorable=max(lo-x['l'] for x in candles)
        if invalid: state='INVALIDATED'
        elif favorable>0: state='REACTED'
        else: state='TESTED'
        out[side]=state; out[side+'_favorable_move']=round(max(0,favorable),2)
    return out

@app.post('/api/outcomes')
def outcomes():
    try:
        d=request.get_json(force=True); setups=(d.get('setups') or [])[:100]
        candles,st,note=fetch_tf('5min',500)
        if not candles:return jsonify({'status':st,'note':note,'outcomes':[]})
        results=[]
        for x in setups:
            # Timestamp filtering prevents old candles before the prediction from grading it.
            t=str(x.get('time') or '').replace('T',' ')[:16]
            after=[c for c in candles if str(c.get('t',''))[:16]>=t] if t else candles
            results.append(evaluate_setup(x,after))
        counts={}
        for r in results:
            for side in ('buy','sell'):
                k=side.upper()+'_'+r[side];counts[k]=counts.get(k,0)+1
        return jsonify({'status':'LIVE_DATA','note':'Deterministic M5 outcome tracking; zone behavior only, not win rate.','counts':counts,'outcomes':results})
    except Exception as e:return jsonify({'error':'outcome_failed','detail':str(e)[:800]}),500

@app.get('/api/replay')
def replay():
    """Quota-free deterministic replay diagnostics over recent M5 history. Not a strategy win-rate backtest."""
    try:
        candles,st,note=fetch_tf('5min',500)
        if not candles:return jsonify({'status':st,'note':note})
        phases={};shocks=0; structures={}; samples=[]
        for i in range(40,len(candles)):
            m=analytics(candles[:i+1]); phases[m.get('market_phase','UNCLEAR')]=phases.get(m.get('market_phase','UNCLEAR'),0)+1
            structures[m.get('structure','UNCLEAR')]=structures.get(m.get('structure','UNCLEAR'),0)+1
            shocks+=1 if m.get('shock_detector')=='TRIGGERED' else 0
            if i%50==0:samples.append({'t':candles[i]['t'],'price':candles[i]['c'],'phase':m.get('market_phase'),'pressure':m.get('current_pressure'),'shock':m.get('shock_detector')})
        return jsonify({'status':'LIVE_DATA','candles_analyzed':len(candles)-40,'phases':phases,'structures':structures,'shock_bars':shocks,'samples':samples,'note':'Replay validates deterministic state logic candle-by-candle. It does not claim strategy profitability.'})
    except Exception as e:return jsonify({'error':'replay_failed','detail':str(e)[:800]}),500

if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.environ.get('PORT',8080)))
