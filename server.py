import os, json, base64, urllib.parse, urllib.request, statistics, time, csv, io
from datetime import datetime, timezone
from flask import Flask, request, jsonify, send_from_directory
from google import genai
from google.genai import types

app = Flask(__name__, static_folder='.', static_url_path='')

PROMPT = r'''
You are Gold Scanner V26.2, a conservative XAUUSD M5 HYBRID OPPORTUNITY + CONFIRMATION ANALYST.
You receive ONE current M5 screenshot plus deterministic H1/M15/M5 market-data metrics fetched automatically from Twelve Data. Use H1/M15 OHLC context internally as confluence/context, but M5 remains the execution timeframe. H1/M15 must NOT automatically veto a valid M5 setup.
Never issue BUY NOW / SELL NOW. Never promise profit, accuracy, or a reversal.

CRITICAL CONFIRMATION RULE (fixes V14 weakness):
- HISTORICAL_REACTION means a zone visibly worked earlier but price has since moved away. It is NOT current entry confirmation.
- CURRENT_CONFIRMATION means the NEWEST visible candles are currently testing/retesting the zone and CLOSED-candle rejection + follow-through/structure evidence exists now.
- A zone far from current price can NEVER be CURRENT_CONFIRMATION just because it reacted earlier.
- If price is between zones, action_state should normally be WAIT.

READING ORDER
1) Newest/right-edge candles first; older candles are context only.
2) PRICE SOURCES: deterministic structure uses exact OHLC. For current-price proximity, use SERVER CONTEXT reference_price when fresh. Also read the newest visible MT5 right-edge price label from the screenshot into current_price when clearly readable. If screenshot and provider reference differ materially, set data_ai_conflict and explain the mismatch; do not silently pretend they are identical.
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
- V26 TIMING: explicitly distinguish UNTESTED future zone, ACTIVE_TEST, ALREADY_REACTED, RETEST_PENDING and INVALIDATED. Never call a recently touched/rejected zone FRESH.
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
- V26 OPPORTUNITY MODE: the scanner is not pullback-only. Evaluate two setup families independently: PULLBACK_CONTINUATION and NEW_MOVE_ORIGIN.
- NEW_MOVE_ORIGIN means an ahead-of-price area where a new bullish/bearish phase could begin if later confirmation develops. It is NOT a prediction that reversal will happen.
- Anchor selection to current price: SELL watch areas must normally be above current price and BUY watch areas below current price. Search outward from current price, but allow a deeper/farther zone to outrank a nearer one when confluence is materially stronger.
- In RANGING/REVERSAL_DEVELOPING conditions, prioritize meaningful range extremes, liquidity pools/sweeps, fresh supply/demand, FVG/OB and structure-transition locations rather than chasing the middle of the range.
- In TRENDING/PULLBACK conditions, preserve continuation pullback areas while also mapping credible opposite-side NEW_MOVE_ORIGIN areas when evidence exists.
- setup_type must be PULLBACK_CONTINUATION, NEW_MOVE_ORIGIN, BOTH, or NONE.

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
 "buy_pullback":{"zone":null,"setup_type":"PULLBACK_CONTINUATION|NEW_MOVE_ORIGIN|BOTH|NONE","freshness":"FRESH|NONE","zone_lifecycle":"FRESH|TESTING|REACTED|RETESTED|CONSUMED|INVALIDATED|EXPIRED|NONE","score":0,"score_components":{"freshness":0,"move_away":0,"structure":0,"touches":0,"proximity":0,"invalidation":0,"momentum":0,"data_agreement":0},"quality":"WEAK|MODERATE|STRONG|VERY_STRONG|NONE","reason":"","confirmation_state":"NO_ZONE|WAIT|TESTING|REJECTION_DETECTED|CONFIRMATION_DEVELOPING|CURRENT_CONFIRMATION|HISTORICAL_REACTION|INVALIDATED","confirmation":"","invalidation":""},
 "sell_pullback":{"zone":null,"setup_type":"PULLBACK_CONTINUATION|NEW_MOVE_ORIGIN|BOTH|NONE","freshness":"FRESH|NONE","zone_lifecycle":"FRESH|TESTING|REACTED|RETESTED|CONSUMED|INVALIDATED|EXPIRED|NONE","score":0,"score_components":{"freshness":0,"move_away":0,"structure":0,"touches":0,"proximity":0,"invalidation":0,"momentum":0,"data_agreement":0},"quality":"WEAK|MODERATE|STRONG|VERY_STRONG|NONE","reason":"","confirmation_state":"NO_ZONE|WAIT|TESTING|REJECTION_DETECTED|CONFIRMATION_DEVELOPING|CURRENT_CONFIRMATION|HISTORICAL_REACTION|INVALIDATED","confirmation":"","invalidation":""},
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
You are Gold Scanner V26 higher-timeframe context extractor. You receive ONE XAUUSD chart screenshot whose timeframe is explicitly H1 or M15. Extract compact context for later M5 analysis. Do not give entries, trade directions, targets, or predictions. Newest/right-edge candles matter most.
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

# V30 FINAL: provider-rate protection. Cache is per Render worker and intentionally conservative.
_DATA_CACHE = {}
_CACHE_TTLS = {'1min':55, '5min':240, '15min':720, '1h':3000, 'price':60, 'DXY':720, 'FRED':21600, 'CFTC':43200, 'futures':720, 'vwap':120, 'orderflow':30}

def _cache_get(key, allow_stale=False):
    item=_DATA_CACHE.get(key)
    if not item:return None, None
    age=max(0,time.time()-item['ts'])
    if allow_stale or age<=item['ttl']:
        return item['value'], round(age,1)
    return None, round(age,1)

def _cache_put(key, value, ttl):
    _DATA_CACHE[key]={'value':value,'ts':time.time(),'ttl':ttl}
    return value

def _is_rate_error(text):
    t=str(text).lower(); return '429' in t or 'too many requests' in t or 'rate limit' in t or 'credits' in t

def fetch_tf(interval, outputsize):
    key=os.environ.get('TWELVE_DATA_API_KEY','').strip()
    if not key: return None, 'DATA_UNAVAILABLE', 'TWELVE_DATA_API_KEY not configured'
    ck=f'xau:{interval}:{outputsize}'; cached,age=_cache_get(ck)
    if cached is not None:return cached,'CACHED_DATA',f'Cached Twelve Data XAU/USD {interval} · cache age {age}s'
    q=urllib.parse.urlencode({'symbol':'XAU/USD','interval':interval,'outputsize':outputsize,'timezone':'UTC','apikey':key})
    try:
        with urllib.request.urlopen('https://api.twelvedata.com/time_series?'+q, timeout=10) as resp:d=json.loads(resp.read().decode())
        if d.get('status')=='error':raise RuntimeError(d.get('message','Twelve Data error'))
        vals=d.get('values') or []
        if len(vals)<25:raise RuntimeError(f'Not enough candles ({len(vals)})')
        candles=[{'t':v['datetime'],'o':float(v['open']),'h':float(v['high']),'l':float(v['low']),'c':float(v['close']), **({'v':float(v['volume'])} if v.get('volume') not in (None,'') else {})} for v in reversed(vals)]
        _cache_put(ck,candles,_CACHE_TTLS.get(interval,300))
        return candles,'LIVE_DATA',f'Twelve Data XAU/USD {interval}'
    except Exception as e:
        stale,stale_age=_cache_get(ck,allow_stale=True)
        if stale is not None:return stale,'STALE_CACHE',f'Provider unavailable/rate-limited; using cached {interval} data · age {stale_age}s · {str(e)[:120]}'
        return None,'DATA_UNAVAILABLE',str(e)[:220]

def fetch_reference_price():
    """Fresh provider reference when affordable; cached fallback prevents 429 storms."""
    key=os.environ.get('TWELVE_DATA_API_KEY','').strip()
    if not key:return None,'UNAVAILABLE','TWELVE_DATA_API_KEY not configured'
    cached,age=_cache_get('xau:price')
    if cached is not None:return cached,'CACHED_REFERENCE',f'Cached reference · age {age}s'
    q=urllib.parse.urlencode({'symbol':'XAU/USD','apikey':key})
    try:
        with urllib.request.urlopen('https://api.twelvedata.com/price?'+q, timeout=10) as resp:d=json.loads(resp.read().decode())
        if d.get('status')=='error':raise RuntimeError(d.get('message','Twelve Data price error'))
        price=float(d.get('price')); _cache_put('xau:price',price,_CACHE_TTLS['price'])
        return price,'LIVE_REFERENCE','Twelve Data /price reference'
    except Exception as e:
        stale,stale_age=_cache_get('xau:price',allow_stale=True)
        if stale is not None:return stale,'STALE_REFERENCE',f'Using cached reference · age {stale_age}s · {str(e)[:100]}'
        return None,'UNAVAILABLE',str(e)[:220]

def candle_age_minutes(candles):
    if not candles:return None
    try:
        raw=str(candles[-1]['t']).replace('T',' ')
        dt=datetime.fromisoformat(raw).replace(tzinfo=timezone.utc)
        return max(0,round((datetime.now(timezone.utc)-dt).total_seconds()/60,1))
    except Exception:return None

def reanchor_candidates(mtf, reference_price):
    """Recompute proximity/depth around the freshest provider reference price without changing structural evidence."""
    if reference_price is None:return
    m5=(mtf.get('M5') or {}).get('metrics') or {}; atr=float(m5.get('atr14') or 1)
    m5['reference_price']=round(float(reference_price),3)
    for side in ('buy','sell'):
        arr=((m5.get('candidate_zones') or {}).get(side) or [])
        for z in arr:
            lo=float(z.get('low')); hi=float(z.get('high'))
            dist=max(0, lo-reference_price) if side=='sell' else max(0, reference_price-hi)
            z['distance_to_reference']=round(dist,3); z['distance_atr']=round(dist/atr,2) if atr else None
            z['side_of_reference']='ABOVE' if lo>reference_price else 'BELOW' if hi<reference_price else 'AT_PRICE'
            rel=max(0,12-min(12,int((dist/atr if atr else 99)*2)))
            z['current_price_relevance']=rel
            family=max(int(z.get('rank_score') or 0), int(z.get('origin_score') or 0) if z.get('setup_type') in ('NEW_MOVE_ORIGIN','BOTH') else 0, int(z.get('continuation_score') or 0) if z.get('setup_type') in ('PULLBACK_CONTINUATION','BOTH') else 0)
            z['opportunity_score']=max(0,min(100,family+rel//4))
        bydist=sorted(arr,key=lambda x:x.get('distance_atr',999)); labels=['SHALLOW','INTERMEDIATE','DEEP','DEEPER']
        for i,z in enumerate(bydist):z['depth']=labels[min(i,len(labels)-1)]
        arr.sort(key=lambda x:(x.get('opportunity_score',0),x.get('rank_score',0)),reverse=True)
    m5['opportunity_map']={'current_price':round(float(reference_price),3),'market_phase':m5.get('market_phase','UNCLEAR'),'buy_watch_areas':((m5.get('candidate_zones') or {}).get('buy') or []),'sell_watch_areas':((m5.get('candidate_zones') or {}).get('sell') or []),'purpose':'Ahead-of-price watch areas anchored to provider reference price. Not predictions.'}

def fetch_multitimeframe():
    specs={'M1':('1min',180),'M5':('5min',240),'M15':('15min',240),'H1':('1h',240)}
    out={}; statuses=[]; notes=[]
    for tf,(interval,n) in specs.items():
        c,st,note=fetch_tf(interval,n); out[tf]={'candles':c,'status':st,'note':note,'metrics':analytics(c) if c else {}}; statuses.append(st); notes.append(tf+': '+note)
    overall='LIVE_DATA' if all(x in ('LIVE_DATA','CACHED_DATA') for x in statuses) else 'PARTIAL_DATA' if any(x in ('LIVE_DATA','CACHED_DATA','STALE_CACHE') for x in statuses) else statuses[0] if statuses else 'DATA_UNAVAILABLE'
    if any(x in ('LIVE_DATA','CACHED_DATA','STALE_CACHE') for x in statuses): enrich_mtf_candidates(out)
    ref,ref_status,ref_note=fetch_reference_price()
    if ref is not None: reanchor_candidates(out,ref)
    m5c=(out.get('M5') or {}).get('candles') or []
    m1c=(out.get('M1') or {}).get('candles') or []
    age=candle_age_minutes(m5c)
    m1_age=candle_age_minutes(m1c)
    # Phase-1 data-quality guard: this does not alter structural point generation.
    # It only marks scans ineligible for the forward-test log when the execution feeds are stale.
    m5_stale=bool(age is None or age>8)
    m1_stale=bool(m1_age is None or m1_age>3)
    test_eligible=not (m5_stale or m1_stale)
    out['_price_meta']={'reference_price':round(ref,3) if ref is not None else None,'reference_status':ref_status,'reference_note':ref_note,'latest_m5_time':m5c[-1]['t'] if m5c else None,'m5_feed_age_minutes':age,'m5_feed_stale':m5_stale,'latest_m1_time':m1c[-1]['t'] if m1c else None,'m1_feed_age_minutes':m1_age,'m1_feed_stale':m1_stale,'phase1_test_eligible':test_eligible,'market_data_inactive':bool(age is not None and age>12),'market_data_note':'MARKET / DATA FEED INACTIVE — analysis uses last available closed candles; lifecycle resumes with fresh M5 data.' if age is not None and age>12 else 'Fresh M5 data available.'}
    return out,overall,' | '.join(notes)+' | PRICE: '+ref_note

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

    # V34.2 balanced order-block heuristic: last opposite candle before a >=1.25 ATR 3-candle displacement.
    order_blocks=[]
    start=max(3,len(c)-45)
    for i in range(start,len(c)-2):
        end=c[i+2]; move_seq=end['c']-c[i]['o']
        if abs(move_seq) < 1.25*(atr or 1): continue
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

    # V34.6 FIVE-CONCEPT SEQUENCE INTELLIGENCE. Supporting context only; these features
    # do not manufacture a zone or become mandatory gates.
    # 1) Market Structure Shift (MSS): a sweep/reclaim plus decisive displacement through structure.
    mss='NONE'
    if sweep=='SELL_SIDE_SWEEP_RECLAIM_UP' and displacement=='BULLISH' and event in ('BULLISH_CHOCH','BULLISH_BOS'):
        mss='BULLISH_MSS'
    elif sweep=='BUY_SIDE_SWEEP_RECLAIM_DOWN' and displacement=='BEARISH' and event in ('BEARISH_CHOCH','BEARISH_BOS'):
        mss='BEARISH_MSS'

    # 2) Liquidity void / Balanced Price Range (BPR): opposing unfilled FVGs that overlap.
    active_bull=[g for g in quality_fvgs if g['type']=='BULLISH_FVG' and g.get('fill_state')!='FILLED']
    active_bear=[g for g in quality_fvgs if g['type']=='BEARISH_FVG' and g.get('fill_state')!='FILLED']
    bprs=[]
    for bg in active_bull[-5:]:
        for sg in active_bear[-5:]:
            lo=max(float(bg['low']),float(sg['low'])); hi=min(float(bg['high']),float(sg['high']))
            if lo < hi:
                bprs.append({'low':round(lo,2),'high':round(hi,2),'state':'BALANCED_PRICE_RANGE'})
    # Recent high-quality one-sided imbalance is treated as a liquidity void context.
    liquidity_void='BULLISH_VOID' if recent_high_q and not recent_low_q else 'BEARISH_VOID' if recent_low_q and not recent_high_q else 'MIXED_OR_NONE'

    # 3) Failed auction / acceptance-vs-rejection quality using several CLOSED candles.
    recent4=c[-4:]
    above=sum(1 for x in recent4 if x['c']>range_hi); below=sum(1 for x in recent4 if x['c']<range_lo)
    if above>=2: auction_state='ACCEPTANCE_ABOVE_RANGE'
    elif below>=2: auction_state='ACCEPTANCE_BELOW_RANGE'
    elif sweep=='BUY_SIDE_SWEEP_RECLAIM_DOWN': auction_state='FAILED_AUCTION_ABOVE'
    elif sweep=='SELL_SIDE_SWEEP_RECLAIM_UP': auction_state='FAILED_AUCTION_BELOW'
    else: auction_state='BALANCED_OR_UNCLEAR'

    # 4) Nested dealing-range hierarchy: broad range plus a recent micro range.
    micro=c[-16:] if len(c)>=16 else c
    micro_hi=max(x['h'] for x in micro); micro_lo=min(x['l'] for x in micro); micro_eq=(micro_hi+micro_lo)/2
    micro_pd='PREMIUM' if last['c']>micro_eq+0.1*(micro_hi-micro_lo) else 'DISCOUNT' if last['c']<micro_eq-0.1*(micro_hi-micro_lo) else 'EQUILIBRIUM'
    dealing_range_hierarchy={'macro':{'low':round(range_lo,2),'equilibrium':round(equilibrium,2),'high':round(range_hi,2),'state':pd},'micro':{'low':round(micro_lo,2),'equilibrium':round(micro_eq,2),'high':round(micro_hi,2),'state':micro_pd}}

    # 5) Draw-on-liquidity / liquidity path: exposed pools are objectives/context, never predictions.
    above_levels=[float(v) for v in ([range_hi]+[x for x in eqh[-2:]]+[x[1] for x in swings_hi[-2:]]) if float(v)>last['c']]
    below_levels=[float(v) for v in ([range_lo]+[x for x in eql[-2:]]+[x[1] for x in swings_lo[-2:]]) if float(v)<last['c']]
    nearest_above=min(above_levels,key=lambda v:v-last['c']) if above_levels else None
    nearest_below=max(below_levels,key=lambda v:v) if below_levels else None
    liquidity_path={'nearest_above':round(nearest_above,2) if nearest_above is not None else None,'nearest_below':round(nearest_below,2) if nearest_below is not None else None,'bias':'ABOVE' if structure=='HH_HL' and nearest_above is not None else 'BELOW' if structure=='LL_LH' and nearest_below is not None else 'TWO_SIDED','note':'Exposed liquidity context only; not a prediction that price must trade there.'}

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
    if mss=='BULLISH_MSS': bull_factors.append('bullish MSS sequence')
    if mss=='BEARISH_MSS': bear_factors.append('bearish MSS sequence')
    if auction_state=='FAILED_AUCTION_BELOW': bull_factors.append('failed auction below')
    if auction_state=='FAILED_AUCTION_ABOVE': bear_factors.append('failed auction above')
    confluence={'bullish':bull_factors,'bearish':bear_factors,'bullish_count':len(bull_factors),'bearish_count':len(bear_factors),'sequence':sequence}

    # V26 multi-candidate opportunity map. Deterministic candidates are ranked evidence locations, not signals.
    cp=last['c']; candidates=[]; ztol=max(atr*0.18,0.25)
    def add_candidate(side,lo,hi,kind,base,meta=None,touch_from=None):
        lo,hi=float(min(lo,hi)),float(max(lo,hi))
        if side=='BUY' and hi>=cp: return
        if side=='SELL' and lo<=cp: return
        # Count interactions. Dynamic break/retest candidates only count candles AFTER
        # the structural break, so the old swing that created the level is not falsely
        # treated as a prior retest.
        recent60=c[-60:] if touch_from is None else c[max(0,int(touch_from)):]
        touches=sum(1 for x in recent60 if x['l']<=hi and x['h']>=lo)
        body_window=recent60[-8:]
        bodies=sum(1 for x in body_window if (side=='BUY' and x['c']<hi) or (side=='SELL' and x['c']>lo))
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
    # V26.2 LOCAL TRANSITION ORIGINS: recent M5 swing/range extremes near price are
    # evaluated independently from continuation pullbacks. This helps surface a nearby
    # possible phase-transition area without assuming price must travel to a deeper zone.
    recent_window=c[-36:] if len(c)>=12 else c
    local_hi=max(x['h'] for x in recent_window); local_lo=min(x['l'] for x in recent_window)
    recent_hi=[x for x in swings_hi if x[0]>=max(0,len(c)-48)][-3:]
    recent_lo=[x for x in swings_lo if x[0]>=max(0,len(c)-48)][-3:]
    for _,v in recent_hi:
        add_candidate('SELL',v-ztol,v+ztol,'LOCAL_BEARISH_ORIGIN',76,{'origin_family':True,'local_transition':True})
    for _,v in recent_lo:
        add_candidate('BUY',v-ztol,v+ztol,'LOCAL_BULLISH_ORIGIN',76,{'origin_family':True,'local_transition':True})
    add_candidate('SELL',local_hi-ztol,local_hi+ztol,'LOCAL_RANGE_HIGH_ORIGIN',74,{'origin_family':True,'local_transition':True})
    add_candidate('BUY',local_lo-ztol,local_lo+ztol,'LOCAL_RANGE_LOW_ORIGIN',74,{'origin_family':True,'local_transition':True})
    # V26 ahead-of-price origin candidates: meaningful range/liquidity extremes can matter before a new move begins.
    add_candidate('BUY',range_lo-ztol,range_lo+ztol,'RANGE_LOW_ORIGIN',70,{'market_phase':phase,'liquidity':'external_below'})
    add_candidate('SELL',range_hi-ztol,range_hi+ztol,'RANGE_HIGH_ORIGIN',70,{'market_phase':phase,'liquidity':'external_above'})
    for v in eql[-2:]: add_candidate('BUY',v-ztol,v+ztol,'EQUAL_LOW_LIQUIDITY',68,{'liquidity_pool':True})
    for v in eqh[-2:]: add_candidate('SELL',v-ztol,v+ztol,'EQUAL_HIGH_LIQUIDITY',68,{'liquidity_pool':True})

    # V30.3 RECENCY-FIRST DYNAMIC PULLBACK ENGINE.
    # A pullback must belong to the latest dominant impulse, not an older opposite leg.
    # Detection is deliberately earlier (ATR-relative), while zone qualification remains strict/fresh-only.
    dynamic={'state':'NONE','direction':'NONE','impulse_atr':0.0,'retracement_atr':0.0,'retracement_ratio':0.0,'fresh_continuation_found':False,'market_state_detected':False,'setup_qualified':False,'note':'No meaningful M5 pullback state detected.'}
    lookback=max(0,len(c)-32)
    recent_seg=c[lookback:]
    if len(recent_seg)>=8:
        low_rel=min(range(len(recent_seg)), key=lambda k: recent_seg[k]['l'])
        high_rel=max(range(len(recent_seg)), key=lambda k: recent_seg[k]['h'])
        low_idx=lookback+low_rel; low_px=recent_seg[low_rel]['l']
        high_idx=lookback+high_rel; high_px=recent_seg[high_rel]['h']

        # Build the bearish leg only from a high that occurred BEFORE the latest low.
        bear_slice=c[max(lookback,low_idx-16):low_idx+1]
        bear_start_rel=max(range(len(bear_slice)), key=lambda k: bear_slice[k]['h']) if bear_slice else 0
        bear_start=max(lookback,low_idx-16)+bear_start_rel
        bear_high=c[bear_start]['h']; bear_imp=(bear_high-low_px)/(atr or 1)
        bear_retrace=max(0.0,(cp-low_px)/(atr or 1)); bear_ratio=bear_retrace/max(bear_imp,1e-9)

        # Build the bullish leg only from a low that occurred BEFORE the latest high.
        bull_slice=c[max(lookback,high_idx-16):high_idx+1]
        bull_start_rel=min(range(len(bull_slice)), key=lambda k: bull_slice[k]['l']) if bull_slice else 0
        bull_start=max(lookback,high_idx-16)+bull_start_rel
        bull_low=c[bull_start]['l']; bull_imp=(high_px-bull_low)/(atr or 1)
        bull_retrace=max(0.0,(high_px-cp)/(atr or 1)); bull_ratio=bull_retrace/max(bull_imp,1e-9)

        bearish_context=(structure=='LL_LH' or pressure in ('BEARISH','EXTREME_BEARISH') or mom.startswith('BEARISH'))
        bullish_context=(structure=='HH_HL' or pressure in ('BULLISH','EXTREME_BULLISH') or mom.startswith('BULLISH'))

        # A true retracement must be materially smaller than the impulse. If price has
        # retraced >85% of an old leg, that old leg cannot label the current pullback.
        # 0.20 ATR allows early detection without calling every tiny opposite candle a pullback.
        bear_active=(bearish_context and bear_imp>=1.25 and bear_retrace>=0.18 and bear_ratio<=0.85 and low_idx<=len(c)-2 and bear_start<low_idx)
        bull_active=(bullish_context and bull_imp>=1.25 and bull_retrace>=0.18 and bull_ratio<=0.85 and high_idx<=len(c)-2 and bull_start<high_idx)

        # Recency wins first: the newest completed impulse extreme is the execution leg.
        # Strength is only a tie-breaker; an older giant move cannot override a newer break.
        choose=None
        if bear_active and bull_active:
            if low_idx>high_idx: choose='BEAR'
            elif high_idx>low_idx: choose='BULL'
            else: choose='BEAR' if bear_imp>=bull_imp else 'BULL'
        elif bear_active: choose='BEAR'
        elif bull_active: choose='BULL'

        # V30.4 STATE/SETUP SEPARATION. If strict setup gates reject both legs,
        # still classify an obvious current retracement from the newest significant
        # impulse extreme. This is informational only and cannot create a zone.
        # The latest significant extreme wins; a zone still needs the stricter rules below.
        if choose is None:
            state_bear=(bear_imp>=1.25 and bear_retrace>=0.18 and bear_ratio<=0.90 and
                        low_idx>=len(c)-10 and bear_start<low_idx and
                        cp>=low_px+0.18*(atr or 1))
            state_bull=(bull_imp>=1.25 and bull_retrace>=0.18 and bull_ratio<=0.90 and
                        high_idx>=len(c)-10 and bull_start<high_idx and
                        cp<=high_px-0.18*(atr or 1))
            if state_bear and state_bull:
                choose='BEAR' if low_idx>high_idx else 'BULL'
            elif state_bear:
                choose='BEAR'
            elif state_bull:
                choose='BULL'

        if choose=='BEAR':
            dynamic={'state':'PULLBACK_STARTING' if bear_retrace<0.45 else 'PULLBACK_IN_PROGRESS','direction':'BEARISH_CONTINUATION','impulse_atr':round(bear_imp,2),'retracement_atr':round(bear_retrace,2),'retracement_ratio':round(bear_ratio,2),'fresh_continuation_found':False,'market_state_detected':True,'setup_qualified':False,'note':'Latest dominant M5 impulse is bearish; an upward retracement is developing. Searching for a fresh first-retest SELL continuation level.'}
            for si,sv in reversed(swings_lo):
                if si>=low_idx or si<max(0,low_idx-35): continue
                breaks=[j for j in range(si+1,low_idx+1) if c[j]['c'] < sv-0.03*atr]
                if not breaks: continue
                bi=breaks[0]; lo,hi=sv-ztol,sv+ztol
                post=c[bi+1:]
                tested=any(x['l']<=hi and x['h']>=lo for x in post)
                if lo>cp and not tested:
                    add_candidate('SELL',lo,hi,'DYNAMIC_BROKEN_SUPPORT_RETEST',82,{'dynamic_pullback':True,'broken_swing':round(sv,2),'break_index':bi,'impulse_extreme_index':low_idx},touch_from=bi+1)
                    dynamic['fresh_continuation_found']=True
                    dynamic['setup_qualified']=True
                    dynamic['candidate_zone']={'side':'SELL','low':round(lo,2),'high':round(hi,2),'source':'DYNAMIC_BROKEN_SUPPORT_RETEST','detected_at':c[-1].get('t'),'status':'DYNAMIC_QUALIFIED'}
                    dynamic['note']='Bearish pullback active; a fresh broken-support first-retest SELL candidate was detected. Final fresh-zone display qualification is checked separately.'
                    break
        elif choose=='BULL':
            dynamic={'state':'PULLBACK_STARTING' if bull_retrace<0.45 else 'PULLBACK_IN_PROGRESS','direction':'BULLISH_CONTINUATION','impulse_atr':round(bull_imp,2),'retracement_atr':round(bull_retrace,2),'retracement_ratio':round(bull_ratio,2),'fresh_continuation_found':False,'market_state_detected':True,'setup_qualified':False,'note':'Latest dominant M5 impulse is bullish; a downward retracement is developing. Searching for a fresh first-retest BUY continuation level.'}
            for si,sv in reversed(swings_hi):
                if si>=high_idx or si<max(0,high_idx-35): continue
                breaks=[j for j in range(si+1,high_idx+1) if c[j]['c'] > sv+0.03*atr]
                if not breaks: continue
                bi=breaks[0]; lo,hi=sv-ztol,sv+ztol
                post=c[bi+1:]
                tested=any(x['l']<=hi and x['h']>=lo for x in post)
                if hi<cp and not tested:
                    add_candidate('BUY',lo,hi,'DYNAMIC_BROKEN_RESISTANCE_RETEST',82,{'dynamic_pullback':True,'broken_swing':round(sv,2),'break_index':bi,'impulse_extreme_index':high_idx},touch_from=bi+1)
                    dynamic['fresh_continuation_found']=True
                    dynamic['setup_qualified']=True
                    dynamic['candidate_zone']={'side':'BUY','low':round(lo,2),'high':round(hi,2),'source':'DYNAMIC_BROKEN_RESISTANCE_RETEST','detected_at':c[-1].get('t'),'status':'DYNAMIC_QUALIFIED'}
                    dynamic['note']='Bullish pullback active; a fresh broken-resistance first-retest BUY candidate was detected. Final fresh-zone display qualification is checked separately.'
                    break
    # Deduplicate overlapping same-side candidates, preserving the stronger one.
    ranked=[]
    for q in sorted(candidates,key=lambda x:x['rank_score'],reverse=True):
        if not any(r['side']==q['side'] and not (q['high']<r['low']-ztol or q['low']>r['high']+ztol) for r in ranked): ranked.append(q)
    candidate_zones={'buy':[x for x in ranked if x['side']=='BUY'][:10],'sell':[x for x in ranked if x['side']=='SELL'][:10]}  # V34.2: preserve a wider candidate pool until freshness filtering

    # V32 TRANSITION ENGINE: detect a developing change of control before a full trend label is obvious.
    # This is state intelligence only; it never creates a BUY/SELL zone or an entry signal.
    bull_score=0; bear_score=0; bull_ev=[]; bear_ev=[]
    if sweep=='SELL_SIDE_SWEEP_RECLAIM_UP': bull_score+=18; bull_ev.append('sell-side sweep + reclaim')
    if sweep=='BUY_SIDE_SWEEP_RECLAIM_DOWN': bear_score+=18; bear_ev.append('buy-side sweep + reclaim')
    if event=='BULLISH_CHOCH': bull_score+=26; bull_ev.append('bullish CHoCH')
    elif event=='BULLISH_BOS': bull_score+=18; bull_ev.append('bullish BOS')
    if event=='BEARISH_CHOCH': bear_score+=26; bear_ev.append('bearish CHoCH')
    elif event=='BEARISH_BOS': bear_score+=18; bear_ev.append('bearish BOS')
    if displacement=='BULLISH': bull_score+=18; bull_ev.append('bullish displacement')
    elif displacement=='BEARISH': bear_score+=18; bear_ev.append('bearish displacement')
    if mom in ('BULLISH','BULLISH_STRONG'): bull_score+=14 if mom=='BULLISH' else 20; bull_ev.append('bullish momentum')
    if mom in ('BEARISH','BEARISH_STRONG'): bear_score+=14 if mom=='BEARISH' else 20; bear_ev.append('bearish momentum')
    if pressure in ('BULLISH','EXTREME_BULLISH'): bull_score+=10; bull_ev.append('bullish pressure')
    if pressure in ('BEARISH','EXTREME_BEARISH'): bear_score+=10; bear_ev.append('bearish pressure')
    if structure=='HH_HL': bull_score+=18; bull_ev.append('HH/HL structure')
    elif structure=='LL_LH': bear_score+=18; bear_ev.append('LL/LH structure')
    if acceptance=='ACCEPTED_ABOVE_SWING': bull_score+=16; bull_ev.append('closed-candle acceptance above swing')
    elif acceptance=='ACCEPTED_BELOW_SWING': bear_score+=16; bear_ev.append('closed-candle acceptance below swing')
    if sequence=='BULLISH_SWEEP_STRUCTURE_FVG': bull_score+=18; bull_ev.append('sweep → structure → FVG sequence')
    elif sequence=='BEARISH_SWEEP_STRUCTURE_FVG': bear_score+=18; bear_ev.append('sweep → structure → FVG sequence')
    # Counter-structure evidence is the important transition clue: do not call a reversal from green/red candles alone.
    prior_bias='BEARISH' if len(swings_hi)>=2 and swings_hi[-1][1] < swings_hi[-2][1] else 'BULLISH' if len(swings_lo)>=2 and swings_lo[-1][1] > swings_lo[-2][1] else 'MIXED'
    dominant='BULLISH' if bull_score>=bear_score+12 else 'BEARISH' if bear_score>=bull_score+12 else 'MIXED'
    dom_score=max(bull_score,bear_score)
    if dominant=='BULLISH':
        if structure=='HH_HL' and bull_score>=58: tstate='BULLISH_STRUCTURE_ESTABLISHED'
        elif bull_score>=44 and any(x in bull_ev for x in ('bullish CHoCH','closed-candle acceptance above swing')): tstate='BULLISH_TRANSITION_DEVELOPING'
        elif bull_score>=28: tstate='POTENTIAL_BULLISH_TRANSITION'
        else: tstate='NO_CLEAR_TRANSITION'
        tev=bull_ev
    elif dominant=='BEARISH':
        if structure=='LL_LH' and bear_score>=58: tstate='BEARISH_STRUCTURE_ESTABLISHED'
        elif bear_score>=44 and any(x in bear_ev for x in ('bearish CHoCH','closed-candle acceptance below swing')): tstate='BEARISH_TRANSITION_DEVELOPING'
        elif bear_score>=28: tstate='POTENTIAL_BEARISH_TRANSITION'
        else: tstate='NO_CLEAR_TRANSITION'
        tev=bear_ev
    else:
        tstate='TRANSITION_CONFLICT' if max(bull_score,bear_score)>=30 else 'NO_CLEAR_TRANSITION'; tev=[]
    transition_engine={'state':tstate,'dominant_side':dominant,'evidence_score':min(100,dom_score),'bullish_score':min(100,bull_score),'bearish_score':min(100,bear_score),'evidence':tev[-6:],'prior_structure_bias':prior_bias,'note':'Closed-candle transition state only. It does not create a trade point; fresh-zone qualification remains separate.'}

    return {'closed_candle_engine':True,'reaction_quality':reaction_quality,'latest_wick_rejection':wick_reject,'recent_bull_candles':bull,'recent_bear_candles':bear,'data_current_price':round(last['c'],3),'atr14':round(atr,3),'structure':structure,'structure_event':event,'momentum':mom,'volatility':vol,'current_pressure':pressure,'market_phase':phase,'shock_detector':shock,'last_candle_range_atr':round(range_atr,2),'last_candle_body_atr':round(body_atr,2),'approach_speed':speed,'move_3bar_atr':round(move3_atr,2),'last_swing_highs':[round(x[1],2) for x in swings_hi[-3:]],'last_swing_lows':[round(x[1],2) for x in swings_lo[-3:]],'equal_highs':eqh[-2:],'equal_lows':eql[-2:],'recent_5bar_move':round(move,3),'avg_body_5':round(avg_body,3),'displacement':displacement,'recent_fvgs':fvgs[-4:],'session_utc':session,'extension_atr_5bar':extension_atr,'chase_risk':chase_risk,'fvg_quality':quality_fvgs[-6:],'order_blocks':obs,'premium_discount':{'state':pd,'range_low':round(range_lo,2),'equilibrium':round(equilibrium,2),'range_high':round(range_hi,2)},'external_liquidity':external_liq,'internal_liquidity':internal_liq,'liquidity_sweep':sweep,'body_acceptance':acceptance,'session_liquidity':session_liq,'price_action_sequence':sequence,'market_structure_shift':mss,'liquidity_void':liquidity_void,'balanced_price_ranges':bprs[-4:],'auction_state':auction_state,'dealing_range_hierarchy':dealing_range_hierarchy,'liquidity_path':liquidity_path,'confluence_cluster':confluence,'candidate_zones':candidate_zones,'dynamic_pullback':dynamic,'transition_engine':transition_engine,'latest_closed_candles':c[-12:]}



def inducement_relationship(m, side, z, atr=None):
    """V34.5 supporting context only: identify minor internal liquidity sitting in front of a candidate.
    This never creates a zone and never vetoes one. It can add a small ranking bonus when the
    geometry is sensible: minor low above BUY demand / minor high below SELL supply.
    """
    try:
        cp=float(m.get('data_current_price')); lo=float(z.get('low')); hi=float(z.get('high'))
        atr=float(atr or m.get('atr14') or 1)
    except (TypeError,ValueError):
        return {'present':False,'level':None,'bonus':0,'note':'NONE'}
    il=m.get('internal_liquidity') or {}
    vals=(il.get('minor_lows') or []) + (il.get('equal_lows') or []) if side=='buy' else (il.get('minor_highs') or []) + (il.get('equal_highs') or [])
    clean=[]
    for v in vals:
        try: clean.append(float(v))
        except (TypeError,ValueError): pass
    # For BUY, a minor low between current price and demand may be swept before demand is tested.
    # For SELL, a minor high between current price and supply may be swept first.
    if side=='buy':
        front=[v for v in clean if hi < v < cp]
        level=min(front, key=lambda v:abs(v-hi)) if front else None
        sensible=level is not None and (level-hi) <= max(atr*1.8,0.35)
    else:
        front=[v for v in clean if cp < v < lo]
        level=min(front, key=lambda v:abs(lo-v)) if front else None
        sensible=level is not None and (lo-level) <= max(atr*1.8,0.35)
    if not sensible:
        return {'present':False,'level':round(level,2) if level is not None else None,'bonus':0,'note':'NONE'}
    return {'present':True,'level':round(level,2),'bonus':4,'note':'Minor internal liquidity/possible inducement sits in front of the candidate; supporting context only.'}

def enrich_mtf_candidates(mtf):
    """V26: rank M5 watch areas with M15/H1 confluence, current-price relevance, and setup type without letting HTF force direction."""
    m5=(mtf.get('M5') or {}).get('metrics') or {}
    m15=(mtf.get('M15') or {}).get('metrics') or {}
    h1=(mtf.get('H1') or {}).get('metrics') or {}
    cp=m5.get('data_current_price'); atr=float(m5.get('atr14') or 1)
    if cp is None:return
    def zones(m,side): return ((m.get('candidate_zones') or {}).get(side) or [])
    def overlap_or_near(a,b,near):
        return not (a['high'] < b['low']-near or a['low'] > b['high']+near)
    for side in ('buy','sell'):
        arr=zones(m5,side)
        for z in arr:
            base=int(z.get('rank_score') or 0); evidence=[]; opposition=[]; bonus=0
            m15_hits=[x for x in zones(m15,side) if overlap_or_near(z,x,max(atr*.35,.35))]
            h1_hits=[x for x in zones(h1,side) if overlap_or_near(z,x,max(atr*.65,.6))]
            if m15_hits: bonus+=10; evidence.append('M15 zone overlap')
            if h1_hits: bonus+=12; evidence.append('H1 zone overlap')
            # Structure is context, not a veto. Small bonus/penalty only.
            bull=(side=='buy')
            for name,m,w in [('M15',m15,5),('H1',h1,4)]:
                st=m.get('structure')
                aligned=(bull and st=='HH_HL') or ((not bull) and st=='LL_LH')
                opposed=(bull and st=='LL_LH') or ((not bull) and st=='HH_HL')
                if aligned: bonus+=w; evidence.append(name+' structure aligned')
                elif opposed: bonus-=max(2,w-2); opposition.append(name+' structure opposed')
            # Premium/discount is location context only.
            pd=h1.get('premium_discount',{}).get('state')
            if bull and pd=='DISCOUNT': bonus+=4; evidence.append('H1 discount')
            elif (not bull) and pd=='PREMIUM': bonus+=4; evidence.append('H1 premium')
            # Liquidity below a BUY / above a SELL can mean price may seek deeper liquidity: caution, not veto.
            ext=h1.get('external_liquidity') or {}
            target=ext.get('below' if bull else 'above')
            if isinstance(target,(int,float)):
                if (bull and target < z['low']) or ((not bull) and target > z['high']): opposition.append('external liquidity remains beyond zone')
            ind=inducement_relationship(m5,side,z,atr)
            if ind.get('present'):
                bonus+=int(ind.get('bonus') or 0); evidence.append('possible inducement/internal liquidity in front of zone')
            z['inducement_context']=ind
            # V34.6 relationship bonuses are deliberately small and never veto a valid fresh zone.
            seq_bonus=0; seq_ctx=[]
            mss=str(m5.get('market_structure_shift') or 'NONE')
            auc=str(m5.get('auction_state') or 'BALANCED_OR_UNCLEAR')
            dr=m5.get('dealing_range_hierarchy') or {}; micro_pd=((dr.get('micro') or {}).get('state'))
            lp=m5.get('liquidity_path') or {}
            bprs=m5.get('balanced_price_ranges') or []
            if (bull and mss=='BULLISH_MSS') or ((not bull) and mss=='BEARISH_MSS'): seq_bonus+=5; seq_ctx.append('MSS aligned')
            if (bull and auc=='FAILED_AUCTION_BELOW') or ((not bull) and auc=='FAILED_AUCTION_ABOVE'): seq_bonus+=4; seq_ctx.append('failed-auction rejection aligned')
            if (bull and micro_pd=='DISCOUNT') or ((not bull) and micro_pd=='PREMIUM'): seq_bonus+=3; seq_ctx.append('micro dealing-range location')
            if any(not (z['high']<float(r['low'])-atr*.2 or z['low']>float(r['high'])+atr*.2) for r in bprs): seq_bonus+=3; seq_ctx.append('BPR/imbalance overlap')
            draw=lp.get('nearest_above' if bull else 'nearest_below')
            if isinstance(draw,(int,float)): seq_bonus+=2; seq_ctx.append('exposed liquidity in setup direction')
            bonus+=min(12,seq_bonus)
            z['sequence_context']={'bonus':min(12,seq_bonus),'evidence':seq_ctx}
            z['m5_base_score']=base; z['mtf_bonus']=bonus; z['rank_score']=max(0,min(100,base+bonus))
            z['mtf_evidence']=evidence; z['mtf_opposition']=opposition
            z['depth']='SHALLOW'
        # Label by distance from current price after re-ranking.
        arr.sort(key=lambda x:x.get('rank_score',0),reverse=True)
        bydist=sorted(arr,key=lambda x:x.get('distance_atr',999))
        labels=['SHALLOW','INTERMEDIATE','DEEP','DEEPER']
        for i,z in enumerate(bydist): z['depth']=labels[min(i,len(labels)-1)]
    # V26 classify why each ahead-of-price area matters. This is evidence classification, never a direction prediction.
    phase=m5.get('market_phase','UNCLEAR'); m5st=m5.get('structure','UNCLEAR'); m15st=m15.get('structure','UNCLEAR')
    seq=str(m5.get('price_action_sequence') or 'NONE')
    for side in ('buy','sell'):
        bull=(side=='buy')
        trend_aligned=(bull and (m5st=='HH_HL' or m15st=='HH_HL')) or ((not bull) and (m5st=='LL_LH' or m15st=='LL_LH'))
        for z in zones(m5,side):
            src=z.get('source')
            origin_source=src in {'RANGE_LOW_ORIGIN','RANGE_HIGH_ORIGIN','EQUAL_LOW_LIQUIDITY','EQUAL_HIGH_LIQUIDITY','SWING_DEMAND','SWING_SUPPLY','LOCAL_BEARISH_ORIGIN','LOCAL_BULLISH_ORIGIN','LOCAL_RANGE_HIGH_ORIGIN','LOCAL_RANGE_LOW_ORIGIN'}
            local_origin=src in {'LOCAL_BEARISH_ORIGIN','LOCAL_BULLISH_ORIGIN','LOCAL_RANGE_HIGH_ORIGIN','LOCAL_RANGE_LOW_ORIGIN'}
            transition_phase=phase in {'RANGING','REVERSAL_DEVELOPING','BREAKOUT','UNCLEAR'}
            seq_support=(bull and seq.startswith('BULLISH')) or ((not bull) and seq.startswith('BEARISH'))
            new_move=(origin_source and transition_phase) or local_origin
            if seq_support: new_move=True
            pullback=trend_aligned and src in {'BULLISH_OB','BEARISH_OB','BULLISH_FVG','BEARISH_FVG','SWING_DEMAND','SWING_SUPPLY','DYNAMIC_BROKEN_SUPPORT_RETEST','DYNAMIC_BROKEN_RESISTANCE_RETEST'}
            z['setup_type']='BOTH' if new_move and pullback else 'NEW_MOVE_ORIGIN' if new_move else 'PULLBACK_CONTINUATION' if pullback else 'WATCH_AREA'
            # Current price ranks relevance AFTER structural candidates exist; it never creates direction.
            dist=float(z.get('distance_atr') or 0)
            relevance=max(0,10-min(10,int(dist*1.5)))
            z['current_price_relevance']=relevance
            # Transparent family scoring: continuation and transition/origin are independent.
            liquidity=18 if ('LIQUIDITY' in src or 'RANGE_' in src or local_origin) else 10
            structure_ev=18 if (seq_support or m5.get('structure_event') in ('BULLISH_BOS','BULLISH_CHOCH','BEARISH_BOS','BEARISH_CHOCH')) else 11
            displacement_ev=17 if m5.get('displacement') not in (None,'NONE','UNCLEAR') else 9
            freshness=max(4,20-min(16,max(0,int(z.get('touch_count') or 0)-1)*4))
            htf=max(4,min(20,10+int(z.get('mtf_bonus') or 0)//2))
            z['origin_score_components']={'liquidity_location':liquidity,'structure_transition':structure_ev,'displacement':displacement_ev,'freshness':freshness,'htf_context':htf}
            z['origin_score']=min(100,liquidity+structure_ev+displacement_ev+freshness+htf)
            z['continuation_score']=min(100,max(0,int(z.get('rank_score') or 0)+(8 if trend_aligned else -12)))
            if z['setup_type']=='NEW_MOVE_ORIGIN': z['opportunity_reason']='Ahead-of-price origin area to monitor for a possible market-phase transition; confirmation is required later.'
            elif z['setup_type']=='PULLBACK_CONTINUATION': z['opportunity_reason']='Ahead-of-price continuation area aligned with existing M5/M15 structure; confirmation is required later.'
            elif z['setup_type']=='BOTH': z['opportunity_reason']='Area has both continuation and possible transition/origin evidence; treat as a watch area, not a forecast.'
            else: z['opportunity_reason']='Structurally relevant ahead-of-price watch area; setup family is not yet clear.'
            family=max(int(z.get('rank_score') or 0), int(z.get('origin_score') or 0) if z.get('setup_type') in ('NEW_MOVE_ORIGIN','BOTH') else 0, int(z.get('continuation_score') or 0) if z.get('setup_type') in ('PULLBACK_CONTINUATION','BOTH') else 0)
            z['opportunity_score']=max(0,min(100,family+relevance//4))
        zones(m5,side).sort(key=lambda x:(x.get('opportunity_score',0),x.get('rank_score',0)),reverse=True)
    m5['candidate_zones']={'buy':zones(m5,'buy'),'sell':zones(m5,'sell')}
    m5['opportunity_map']={'current_price':cp,'market_phase':phase,'buy_watch_areas':zones(m5,'buy'),'sell_watch_areas':zones(m5,'sell'),'purpose':'Ahead-of-price watch areas for either pullback continuation or a possible new-move origin. Not predictions.'}
    # Closed-candle confirmation evidence around the strongest candidates.
    candles=m5.get('latest_closed_candles') or []
    for side in ('buy','sell'):
        for z in zones(m5,side):
            lo,hi=z['low'],z['high']; recent=candles[-6:]; touched=[x for x in recent if x['l']<=hi and x['h']>=lo]
            z['confirmation_stage']='WAIT'
            if touched:
                z['confirmation_stage']='TESTING'
                last=recent[-1] if recent else None
                if last:
                    body=max(abs(last['c']-last['o']),atr*.05); lower=last['c']-last['l']; upper=last['h']-last['c']
                    reject=(side=='buy' and lower>=1.4*body and last['c']>=lo) or (side=='sell' and upper>=1.4*body and last['c']<=hi)
                    if reject:z['confirmation_stage']='REJECTION_DETECTED'
                if len(recent)>=3:
                    a,b=recent[-2],recent[-1]
                    follow=(side=='buy' and a['c']>a['o'] and b['c']>a['h']) or (side=='sell' and a['c']<a['o'] and b['c']<a['l'])
                    if follow:z['confirmation_stage']='FOLLOW_THROUGH'
            # Acceptance through zone overrides a pretty wick.
            if recent:
                accepted=sum(1 for x in recent[-3:] if (side=='buy' and x['c']<lo) or (side=='sell' and x['c']>hi))>=2
                if accepted:z['confirmation_stage']='INVALIDATED'

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

def norm(r,metrics,data_status,event_risk,m5_live=None):
    if not isinstance(r,dict):r={}
    # Lifecycle only needs M5 OHLC. Do not disable it just because H1 or M15 had a temporary fetch failure.
    if m5_live is None: m5_live = (data_status=='LIVE_DATA')
    visual_cp=None
    try: visual_cp=float(r.get('current_price')) if r.get('current_price') is not None else None
    except: visual_cp=None
    ref_cp=metrics.get('reference_price') if m5_live else None
    # In hybrid mode, a clearly read screenshot price is closest to the user's broker view. Fall back to provider reference, then candle close.
    r['screenshot_price']=visual_cp
    r['provider_reference_price']=ref_cp
    r['latest_m5_feed_close']=metrics.get('data_current_price') if m5_live else None
    r['current_price']=visual_cp if visual_cp is not None else ref_cp if ref_cp is not None else metrics.get('data_current_price') if m5_live else None
    for k,allowed,default in [('m5_state',{'BULLISH','BEARISH','UNCLEAR'},'UNCLEAR'),('structure',{'HH_HL','LL_LH','MIXED','UNCLEAR'},'UNCLEAR'),('structure_event',{'BULLISH_BOS','BEARISH_BOS','BULLISH_CHOCH','BEARISH_CHOCH','NONE','UNCLEAR'},'UNCLEAR'),('volatility',{'LOW','NORMAL','HIGH','EXTREME'},'NORMAL'),('momentum',{'BULLISH_STRONG','BULLISH','NEUTRAL','BEARISH','BEARISH_STRONG','UNCLEAR'},'UNCLEAR')]:
        v=str(r.get(k) or default).upper(); r[k]=v if v in allowed else default
    # Deterministic V19 fields override visual guesses when live data exists.
    if m5_live:
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
            r[side]={'zone':None,'setup_type':'NONE','freshness':'NONE','zone_lifecycle':'NONE','score':0,'score_components':{},'quality':'NONE','reason':z.get('reason') or 'No clear zone.','confirmation_state':'NO_ZONE','confirmation':'','invalidation':'','timing_status':'NO_ZONE','timing_note':'','distance_to_zone':None,'distance_atr':None};continue
        s=clamp(z.get('score')); st=str(z.get('confirmation_state') or 'WAIT').upper(); st=st if st in valid else 'WAIT'
        conf=(z.get('confirmation') or '').lower()
        if st=='CURRENT_CONFIRMATION' and not any(w in conf for w in ('current','newest','retest','testing','now','latest')): st='HISTORICAL_REACTION'
        z.update({'score':s,'quality':qual(s),'confirmation_state':st}); z.setdefault('score_components',{})
        for k in ('reason','confirmation','invalidation'):z.setdefault(k,'')
        if m5_live:
            z=reconcile_zone_lifecycle(z,'buy' if side=='buy_pullback' else 'sell',metrics,cp)
            # Attach deterministic V26 setup-family classification to Gemini's displayed zone when boundaries overlap.
            bounds=zone_bounds(z.get('zone')); candidates=((metrics.get('candidate_zones') or {}).get('buy' if side=='buy_pullback' else 'sell') or [])
            if bounds and candidates:
                lo,hi=bounds; matches=[q for q in candidates if not (hi < q.get('low',0) or lo > q.get('high',0))]
                if matches:
                    best=max(matches,key=lambda q:q.get('opportunity_score',q.get('rank_score',0)))
                    z['setup_type']=best.get('setup_type','WATCH_AREA'); z['opportunity_reason']=best.get('opportunity_reason',''); z['opportunity_score']=best.get('opportunity_score',best.get('rank_score'))
            z.setdefault('setup_type','WATCH_AREA')
        else:
            life=str(z.get('zone_lifecycle') or 'FRESH').upper(); z['zone_lifecycle']=life if life in {'FRESH','TESTING','REACTED','RETESTED','CONSUMED','INVALIDATED','EXPIRED'} else 'FRESH'; z.setdefault('timing_status','VISUAL_ONLY'); z.setdefault('timing_note','M5 lifecycle fallback: live M5 OHLC was unavailable for this scan, so timing is visual-only.'); z.setdefault('distance_to_zone',None); z.setdefault('distance_atr',None)
        r[side]=z
    # V22 active-setup summary separates mapped locations from what is actionable now.
    active=[]
    for name,side in [('BUY','buy_pullback'),('SELL','sell_pullback')]:
        z=r[side]
        if z.get('confirmation_state') in {'CURRENT_CONFIRMATION','CONFIRMATION_DEVELOPING','REJECTION_DETECTED'} and z.get('zone_lifecycle') not in {'REACTED','CONSUMED','INVALIDATED','EXPIRED'}: active.append(name)
    r['active_setup']=' + '.join(active) if active else 'NO_ACTIVE_SETUP'
    r['candidate_zones']=metrics.get('candidate_zones',{}) if m5_live else {}; r['opportunity_map']=metrics.get('opportunity_map',{}) if m5_live else {}
    r['timing_summary']='V26 maps ahead-of-price watch areas for both pullback continuation and possible new-move origins, then tracks lifecycle/confirmation separately.'
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
            if tf.startswith('_'): continue
            c=v.get('candles') or []; m=v.get('metrics') or {}
            details[tf]={
                'status':v.get('status'),'candles_received':len(c),'latest_time':c[-1]['t'] if c else None,
                'latest_close':c[-1]['c'] if c else None,'structure':m.get('structure'),'structure_event':m.get('structure_event'),
                'momentum':m.get('momentum'),'atr14':m.get('atr14'),'candidate_zones':m.get('candidate_zones',{})
            }
        return jsonify({'status':status,'gemini_used':False,'symbol':'XAU/USD','price_meta':mtf.get('_price_meta',{}),'timeframes':details,'note':note})
    except Exception as e:return jsonify({'error':'ohlc_test_failed','detail':str(e)[:900]}),500



def _get_json(url, timeout=10):
    req=urllib.request.Request(url, headers={'User-Agent':'GoldScannerV28/1.0'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())

def fetch_twelve_symbol(symbol, interval='15min', outputsize=80):
    key=os.environ.get('TWELVE_DATA_API_KEY','').strip()
    if not key:return None,'UNAVAILABLE','TWELVE_DATA_API_KEY not configured'
    ck=f'other:{symbol}:{interval}:{outputsize}'; cached,age=_cache_get(ck)
    if cached is not None:return cached,'CACHED_DATA',f'Cached {symbol} {interval} · age {age}s'
    q=urllib.parse.urlencode({'symbol':symbol,'interval':interval,'outputsize':outputsize,'timezone':'UTC','apikey':key})
    try:
        d=_get_json('https://api.twelvedata.com/time_series?'+q)
        if d.get('status')=='error':raise RuntimeError(d.get('message','Twelve Data error'))
        vals=d.get('values') or []
        if len(vals)<12:raise RuntimeError('Not enough observations')
        c=[{'t':v['datetime'],'o':float(v['open']),'h':float(v['high']),'l':float(v['low']),'c':float(v['close']), **({'v':float(v['volume'])} if v.get('volume') not in (None,'') else {})} for v in reversed(vals)]
        _cache_put(ck,c,_CACHE_TTLS.get('futures' if symbol==os.environ.get('GOLD_FUTURES_SYMBOL','') else 'DXY',720))
        return c,'LIVE_DATA',f'Twelve Data {symbol} {interval}'
    except Exception as e:
        stale,sa=_cache_get(ck,allow_stale=True)
        if stale is not None:return stale,'STALE_CACHE',f'Cached fallback {symbol} · age {sa}s'
        return None,'UNAVAILABLE',str(e)[:180]

def fetch_usd_context():
    # DXY is context only. If the provider/plan does not expose it, the scanner continues without it.
    errors=[]
    for sym in ('DXY','USDX'):
        c,st,note=fetch_twelve_symbol(sym,'15min',80)
        if c:
            a=analytics(c); return {'status':'LIVE_DATA','symbol':sym,'price':c[-1]['c'],'structure':a.get('structure'),'momentum':a.get('momentum'),'pressure':a.get('current_pressure'),'move_5':a.get('recent_5bar_move'),'note':note}
        errors.append(sym+': '+note)
    return {'status':'UNAVAILABLE','note':' | '.join(errors)}

def fetch_fred_series(series_id):
    cached,age=_cache_get('fred:'+series_id)
    if cached is not None:return cached,None
    key=os.environ.get('FRED_API_KEY','').strip()
    if not key:return None,'FRED_API_KEY not configured'
    q=urllib.parse.urlencode({'series_id':series_id,'api_key':key,'file_type':'json','sort_order':'desc','limit':8})
    try:
        d=_get_json('https://api.stlouisfed.org/fred/series/observations?'+q)
        obs=[]
        for x in d.get('observations') or []:
            if x.get('value') not in (None,'.'):
                obs.append({'date':x.get('date'),'value':float(x['value'])})
        _cache_put('fred:'+series_id,obs,_CACHE_TTLS['FRED']); return obs,None
    except Exception as e:
        stale,_=_cache_get('fred:'+series_id,allow_stale=True)
        return (stale,None) if stale is not None else (None,str(e)[:180])

def fetch_rates_context():
    # Daily macro context, not an intraday trigger. DGS2/DGS10 = nominal Treasury yields; DFII10 = 10Y real yield.
    out={'status':'UNAVAILABLE','series':{}}
    if not os.environ.get('FRED_API_KEY','').strip():
        out['note']='Optional FRED_API_KEY not configured'; return out
    for sid,label in [('DGS2','US_2Y'),('DGS10','US_10Y'),('DFII10','US_10Y_REAL')]:
        obs,err=fetch_fred_series(sid)
        if obs:
            latest=obs[0]; prior=obs[min(1,len(obs)-1)]
            out['series'][label]={'value':latest['value'],'date':latest['date'],'change':round(latest['value']-prior['value'],4)}
        else: out['series'][label]={'error':err}
    if any('value' in x for x in out['series'].values()):out['status']='LIVE_DATA'
    out['note']='FRED daily macro context; not an intraday execution quote.'
    return out

def fetch_calendar_context():
    key=os.environ.get('TRADING_ECONOMICS_KEY','').strip()
    if not key:return {'status':'UNAVAILABLE','risk':'UNKNOWN','events':[],'note':'Optional TRADING_ECONOMICS_KEY not configured'}
    now=datetime.now(timezone.utc); start=now.strftime('%Y-%m-%d'); end=(now+__import__('datetime').timedelta(days=1)).strftime('%Y-%m-%d')
    # Trading Economics documents /calendar/country/{country}/{from}/{to}. c accepts account credentials/key.
    url='https://api.tradingeconomics.com/calendar/country/united%20states/'+start+'/'+end+'?'+urllib.parse.urlencode({'c':key})
    try:
        d=_get_json(url)
        if not isinstance(d,list):return {'status':'UNAVAILABLE','risk':'UNKNOWN','events':[],'note':'Unexpected calendar response'}
        events=[]
        for e in d:
            imp=int(e.get('Importance') or 0)
            name=str(e.get('Event') or e.get('Category') or '')
            # Keep high-impact plus the most gold-sensitive medium events.
            important=imp>=3 or any(k in name.lower() for k in ('fed','fomc','powell','inflation','cpi','pce','payroll','non farm','unemployment','ppi','gdp','retail sales'))
            if not important:continue
            raw=e.get('Date') or e.get('date')
            try:
                dt=datetime.fromisoformat(str(raw).replace('Z','+00:00'))
                if dt.tzinfo is None:dt=dt.replace(tzinfo=timezone.utc)
                mins=round((dt-now).total_seconds()/60)
            except Exception:mins=None
            events.append({'event':name,'importance':imp,'time':raw,'minutes_from_now':mins,'actual':e.get('Actual'),'forecast':e.get('Forecast'),'previous':e.get('Previous')})
        near=[x for x in events if x['minutes_from_now'] is not None and -30<=x['minutes_from_now']<=60]
        risk='HIGH' if any(x['importance']>=3 for x in near) else 'ELEVATED' if near else 'NORMAL'
        return {'status':'LIVE_DATA','risk':risk,'events':events[:12],'near_events':near[:6],'note':'US economic calendar context'}
    except Exception as e:return {'status':'UNAVAILABLE','risk':'UNKNOWN','events':[],'note':str(e)[:180]}

def build_session_level_context(mtf):
    """Deterministic session + previous day/week liquidity map from M5 OHLC."""
    c=(mtf.get('M5') or {}).get('candles') or []
    if not c:return {'status':'UNAVAILABLE'}
    from collections import defaultdict
    def dt(x):
        try:return datetime.fromisoformat(str(x['t']).replace('T',' ')).replace(tzinfo=timezone.utc)
        except:return None
    rows=[(dt(x),x) for x in c]; rows=[x for x in rows if x[0]]
    if not rows:return {'status':'UNAVAILABLE'}
    byday=defaultdict(list)
    for d,x in rows: byday[d.date()].append((d,x))
    days=sorted(byday)
    latest=days[-1]
    prev=days[-2] if len(days)>=2 else None
    def hilo(xs):
        if not xs:return None
        vals=[x for _,x in xs]
        return {'high':round(max(x['h'] for x in vals),2),'low':round(min(x['l'] for x in vals),2),'open':round(vals[0]['o'],2),'close':round(vals[-1]['c'],2)}
    def window(xs,a,b):return hilo([(d,x) for d,x in xs if a<=d.hour<b])
    cur=byday[latest]
    sessions={'asia':window(cur,0,7),'london':window(cur,7,12),'new_york':window(cur,12,21),'london_opening_range':window(cur,7,8),'new_york_opening_range':window(cur,12,13)}
    previous_day=hilo(byday[prev]) if prev else None
    latest_dt=rows[-1][0]; week_start=(latest_dt.date()-__import__('datetime').timedelta(days=latest_dt.weekday()))
    prior_week_start=week_start-__import__('datetime').timedelta(days=7)
    prior_week_end=week_start-__import__('datetime').timedelta(days=1)
    prior_week=[(d,x) for d,x in rows if prior_week_start<=d.date()<=prior_week_end]
    previous_week=hilo(prior_week)
    cp=float((mtf.get('_price_meta') or {}).get('reference_price') or rows[-1][1]['c'])
    levels=[]
    def add(name,obj):
        if not obj:return
        for k in ('high','low','open','close'):
            if k in obj and obj[k] is not None:levels.append({'name':name+'_'+k.upper(),'price':obj[k],'distance':round(abs(cp-obj[k]),2)})
    add('PREV_DAY',previous_day); add('PREV_WEEK',previous_week)
    for n,o in sessions.items():
        if o:
            for k in ('high','low'): levels.append({'name':n.upper()+'_'+k.upper(),'price':o[k],'distance':round(abs(cp-o[k]),2)})
    levels.sort(key=lambda z:z['distance'])
    # Session sweep/reclaim heuristic using last 3 closed candles around established session levels.
    sweep='NONE'; recent=[x for _,x in rows[-3:]]
    for n,o in sessions.items():
        if not o or not recent:continue
        hi,lo=o['high'],o['low']; last=recent[-1]
        if any(x['h']>hi for x in recent[:-1]) and last['c']<hi:sweep=n.upper()+'_HIGH_SWEEP_RECLAIM_DOWN'
        if any(x['l']<lo for x in recent[:-1]) and last['c']>lo:sweep=n.upper()+'_LOW_SWEEP_RECLAIM_UP'
    return {'status':'LIVE_DATA','latest_utc_day':str(latest),'sessions':sessions,'previous_day':previous_day,'previous_week':previous_week,'nearest_levels':levels[:10],'session_sweep':sweep}

def build_volatility_regime(mtf):
    c=(mtf.get('M5') or {}).get('candles') or []
    if len(c)<40:return {'status':'UNAVAILABLE'}
    trs=[]
    for i in range(1,len(c)):
        prev=c[i-1]['c']; x=c[i]; trs.append(max(x['h']-x['l'],abs(x['h']-prev),abs(x['l']-prev)))
    def atr_at(end,n=14):
        xs=trs[max(0,end-n):end]; return sum(xs)/len(xs) if xs else 0
    hist=[atr_at(i) for i in range(14,len(trs)+1)]; current=hist[-1]
    pct=round(100*sum(1 for x in hist if x<=current)/len(hist),1)
    state='EXTREME' if pct>=90 else 'HIGH' if pct>=70 else 'LOW' if pct<=30 else 'NORMAL'
    return {'status':'LIVE_DATA','atr14':round(current,3),'atr_percentile':pct,'regime':state,'sample_count':len(hist)}

def build_volume_context(mtf):
    c=(mtf.get('M5') or {}).get('candles') or []
    vols=[x.get('v') for x in c if isinstance(x.get('v'),(int,float))]
    if len(vols)<20:return {'status':'UNAVAILABLE','note':'Provider did not supply reliable volume for XAU/USD. No synthetic volume is invented.'}
    recent=vols[-20:]; avg=sum(recent[:-1])/max(1,len(recent)-1); ratio=recent[-1]/avg if avg else None
    state='SURGE' if ratio and ratio>=1.8 else 'ABOVE_AVERAGE' if ratio and ratio>=1.2 else 'QUIET' if ratio and ratio<0.7 else 'NORMAL'
    return {'status':'LIVE_DATA','latest_volume':recent[-1],'volume_ratio_20':round(ratio,2) if ratio else None,'state':state,'note':'Provider volume/tick-volume context; not centralized global spot-gold volume.'}

def fetch_optional_gold_futures():
    sym=os.environ.get('GOLD_FUTURES_SYMBOL','').strip()
    if not sym:return {'status':'UNAVAILABLE','note':'Optional GOLD_FUTURES_SYMBOL not configured; no futures symbol is guessed.'}
    c,st,note=fetch_twelve_symbol(sym,'15min',100)
    if not c:return {'status':'UNAVAILABLE','symbol':sym,'note':note}
    a=analytics(c)
    return {'status':'LIVE_DATA','symbol':sym,'price':c[-1]['c'],'structure':a.get('structure'),'momentum':a.get('momentum'),'pressure':a.get('current_pressure'),'candles':c,'note':note}



def _vwap_calc(rows, label='VWAP'):
    rows=[x for x in (rows or []) if isinstance(x.get('v'),(int,float)) and x.get('v',0)>0]
    if len(rows)<3:
        return {'status':'UNAVAILABLE','note':f'Not enough trustworthy reported volume for {label}; no synthetic volume is invented.'}
    vv=sum(float(x['v']) for x in rows)
    if vv<=0:return {'status':'UNAVAILABLE','note':f'Volume sum is zero; {label} unavailable.'}
    pv=sum(((float(x['h'])+float(x['l'])+float(x['c']))/3.0)*float(x['v']) for x in rows)
    v=pv/vv; last=float(rows[-1]['c'])
    return {'status':'LIVE_DATA','vwap':round(v,3),'last_price':round(last,3),'price_vs_vwap':'ABOVE' if last>v else 'BELOW' if last<v else 'AT','distance':round(last-v,3),'bars':len(rows),'note':f'{label} calculated only from candles containing reported volume.'}

def _hour_of(c):
    try:return int(str(c.get('t',''))[11:13])
    except:return -1

def _daily_and_session_vwap(candles):
    rows=[x for x in (candles or []) if isinstance(x.get('v'),(int,float)) and x.get('v',0)>0]
    if len(rows)<3:
        note='Provider did not supply enough trustworthy reported volume; Daily/Session VWAP unavailable and no synthetic VWAP is invented.'
        return {'status':'UNAVAILABLE','daily':{'status':'UNAVAILABLE'},'session':{'status':'UNAVAILABLE'},'note':note}
    day=str(rows[-1].get('t',''))[:10]; today=[x for x in rows if str(x.get('t',''))[:10]==day]
    daily=_vwap_calc(today,'Daily VWAP')
    h=_hour_of(rows[-1])
    if 0<=h<7: name,a,b='ASIA',0,7
    elif 7<=h<12: name,a,b='LONDON',7,12
    elif 12<=h<21: name,a,b='NEW_YORK',12,21
    else: name,a,b='OFF_HOURS',21,24
    sess=[x for x in today if a<=_hour_of(x)<b]
    session=_vwap_calc(sess,'Session VWAP'); session['session_name']=name
    return {'status':'LIVE_DATA' if daily.get('status')=='LIVE_DATA' or session.get('status')=='LIVE_DATA' else 'UNAVAILABLE','daily':daily,'session':session,'session_name':name,'session_date':day,'note':'Daily and active-session VWAP use reported volume only.'}

def _confirmed_swings(rows, lookback=80):
    a=(rows or [])[-lookback:]; lows=[]; highs=[]
    for i in range(2,len(a)-2):
        if float(a[i]['l'])<min(float(a[i-1]['l']),float(a[i-2]['l']),float(a[i+1]['l']),float(a[i+2]['l'])): lows.append(i)
        if float(a[i]['h'])>max(float(a[i-1]['h']),float(a[i-2]['h']),float(a[i+1]['h']),float(a[i+2]['h'])): highs.append(i)
    return a,lows,highs

def _objective_avwap(candles):
    rows=[x for x in (candles or []) if isinstance(x.get('v'),(int,float)) and x.get('v',0)>0]
    if len(rows)<12:return {'status':'UNAVAILABLE','note':'Not enough trustworthy volume-bearing candles for objective AVWAP.'}
    a,lows,highs=_confirmed_swings(rows)
    out={'status':'LIVE_DATA','method':'LATEST_CONFIRMED_5_BAR_SWING','note':'AVWAP anchors are objective latest confirmed swing low/high; anchors are not chosen after seeing the outcome.'}
    for key,idxs,label in [('bullish',lows,'Bullish AVWAP'),('bearish',highs,'Bearish AVWAP')]:
        if not idxs: out[key]={'status':'UNAVAILABLE'}; continue
        i=idxs[-1]; calc=_vwap_calc(a[i:],label); calc['anchor_time']=a[i]['t']; calc['anchor_price']=round(float(a[i]['l'] if key=='bullish' else a[i]['h']),3); out[key]=calc
    if all((out.get(k) or {}).get('status')!='LIVE_DATA' for k in ('bullish','bearish')):out['status']='UNAVAILABLE'
    return out

def _shift_vwap_values(obj, basis):
    if not isinstance(obj,dict):return obj
    for k,v in list(obj.items()):
        if isinstance(v,dict):_shift_vwap_values(v,basis)
    if obj.get('status')=='LIVE_DATA':
        for k in ('vwap','last_price','anchor_price'):
            if isinstance(obj.get(k),(int,float)):obj[k]=round(float(obj[k])+basis,3)
        if isinstance(obj.get('last_price'),(int,float)) and isinstance(obj.get('vwap'),(int,float)):
            obj['distance']=round(obj['last_price']-obj['vwap'],3); obj['price_vs_vwap']='ABOVE' if obj['last_price']>obj['vwap'] else 'BELOW' if obj['last_price']<obj['vwap'] else 'AT'
    return obj

def build_vwap_context(mtf, futures_ctx):
    """V37 Daily/Session VWAP + objective AVWAP. Prefer volume-bearing futures; basis-adjust to spot before comparing with spot zones."""
    fc=(futures_ctx or {}).get('candles') or []; source='GOLD_FUTURES' if fc else 'XAU_USD_PROVIDER_VOLUME'
    rows=fc or ((mtf.get('M1') or {}).get('candles') or [])
    pack=_daily_and_session_vwap(rows); av=_objective_avwap(rows)
    basis=0.0
    if fc:
        spot=((mtf.get('M1') or {}).get('candles') or [])
        if spot and fc:
            basis=float(spot[-1]['c'])-float(fc[-1]['c'])
            _shift_vwap_values(pack,basis); _shift_vwap_values(av,basis)
    pack['source']=source; pack['symbol']=(futures_ctx or {}).get('symbol') if fc else 'XAU/USD'; pack['basis_adjustment']=round(basis,3) if fc else 0.0; pack['avwap']=av
    # backwards-compatible top-level VWAP uses Daily first, then Session.
    primary=pack.get('daily') if (pack.get('daily') or {}).get('status')=='LIVE_DATA' else pack.get('session')
    if isinstance(primary,dict) and primary.get('status')=='LIVE_DATA':
        pack.update({k:primary.get(k) for k in ('vwap','last_price','price_vs_vwap','distance','bars')})
        pack['status']='LIVE_DATA'
    else:
        pack['status']='UNAVAILABLE'; pack['note']='Daily/Session VWAP + AVWAP are ready, but no trustworthy reported volume is currently available. Nothing is fabricated.'
    return pack

def build_orderflow_context(futures_ctx):
    """True order flow requires aggressor/bid-ask volume. OHLCV alone is deliberately not mislabeled as order flow."""
    # Reserved adapter: a future provider can populate bid_volume/ask_volume per candle.
    rows=(futures_ctx or {}).get('candles') or []
    usable=[x for x in rows if isinstance(x.get('bid_volume'),(int,float)) and isinstance(x.get('ask_volume'),(int,float))]
    if len(usable)<3:
        return {'status':'UNAVAILABLE','state':'WAITING_FOR_TRUE_ORDER_FLOW_DATA','delta':None,'imbalance':None,'note':'No true bid/ask aggressor-volume feed is connected. OHLCV is not being faked into order flow.'}
    recent=usable[-10:]; buy=sum(x['ask_volume'] for x in recent); sell=sum(x['bid_volume'] for x in recent); total=buy+sell; delta=buy-sell
    ratio=(delta/total) if total else 0
    state='BUYERS_AGGRESSIVE' if ratio>=.12 else 'SELLERS_AGGRESSIVE' if ratio<=-.12 else 'BALANCED'
    return {'status':'LIVE_DATA','state':state,'delta':round(delta,2),'imbalance':round(ratio,3),'sample_bars':len(recent),'note':'True order-flow context from connected bid/ask aggressor volume; confirmation context only.'}

def apply_microstructure_context(mtf, vwap, orderflow):
    """V37 annotate existing M1 points with Daily/Session VWAP + objective AVWAP. Never create/delete/move/hard-veto a structural point."""
    m5=(mtf.get('M5') or {}).get('metrics') or {}; p=m5.get('m1_precision') or {}
    m1atr=float(((mtf.get('M1') or {}).get('metrics') or {}).get('atr14') or 0)
    daily=((vwap or {}).get('daily') or {}).get('vwap'); session=((vwap or {}).get('session') or {}).get('vwap'); av=(vwap or {}).get('avwap') or {}
    bullav=(av.get('bullish') or {}).get('vwap'); bearav=(av.get('bearish') or {}).get('vwap'); of=(orderflow or {}).get('state')
    for z in p.get('candidates') or []:
        side=str(z.get('side','')).upper(); lo=float(z.get('low',0)); hi=float(z.get('high',0)); mid=(lo+hi)/2; tol=max(m1atr*.50,0.20)
        vals=[('DAILY_VWAP',daily),('SESSION_VWAP',session),('AVWAP',bullav if side=='BUY' else bearav)]
        near=[name for name,val in vals if isinstance(val,(int,float)) and lo-tol<=float(val)<=hi+tol]
        available=[(name,float(val)) for name,val in vals if isinstance(val,(int,float))]
        if near: state='SUPPORTIVE'
        elif not available: state='UNAVAILABLE'
        else:
            adverse=all((val < lo-tol if side=='BUY' else val > hi+tol) for _,val in available)
            state='CONFLICTING' if adverse else 'NEUTRAL'
        z['vwap_context']=state
        z['vwap_detail']={'daily_vwap':daily,'session_vwap':session,'avwap':bullav if side=='BUY' else bearav,'near_zone':near,'source':(vwap or {}).get('source'),'basis_adjustment':(vwap or {}).get('basis_adjustment',0)}
        z['avwap_context']='SUPPORTIVE' if 'AVWAP' in near else 'UNAVAILABLE' if not isinstance((bullav if side=='BUY' else bearav),(int,float)) else 'NEUTRAL'
        z['orderflow_context']='WAITING' if (orderflow or {}).get('status')!='LIVE_DATA' else ('SUPPORTIVE' if (side=='BUY' and of=='BUYERS_AGGRESSIVE') or (side=='SELL' and of=='SELLERS_AGGRESSIVE') else 'CONFLICTING' if (side=='BUY' and of=='SELLERS_AGGRESSIVE') or (side=='SELL' and of=='BUYERS_AGGRESSIVE') else 'NEUTRAL')
        z['microstructure_note']='V37 VWAP/AVWAP annotate this already-created structural point only; they do not manufacture, move or veto it.'
    m5['m1_precision']=p

def fetch_cftc_gold_positioning():
    """Weekly CFTC disaggregated futures positioning. Context only; never an M5 trigger."""
    cached,age=_cache_get('cftc:gold')
    if cached is not None:return cached
    url='https://www.cftc.gov/dea/newcot/f_disagg.txt'
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'GoldScannerV30/1.0'})
        with urllib.request.urlopen(req,timeout=12) as resp:text=resp.read().decode('utf-8-sig','replace')
        rows=list(csv.DictReader(io.StringIO(text)))
        row=next((r for r in rows if 'GOLD' in str(r.get('Market_and_Exchange_Names','')).upper() and ('COMMODITY EXCHANGE' in str(r.get('Market_and_Exchange_Names','')).upper() or str(r.get('CFTC_Contract_Market_Code','')).strip()=='088691')),None)
        if not row:raise RuntimeError('Gold row not found in weekly CFTC report')
        def num(*keys):
            for k in keys:
                if k in row and str(row[k]).strip():
                    try:return float(str(row[k]).replace(',',''))
                    except:pass
            return None
        long=num('M_Money_Positions_Long_All','M_Money_Positions_Long_Old')
        short=num('M_Money_Positions_Short_All','M_Money_Positions_Short_Old')
        net=(long-short) if long is not None and short is not None else None
        out={'status':'LIVE_DATA','report_date':row.get('Report_Date_as_YYYY-MM-DD') or row.get('As_of_Date_In_Form_YYMMDD'),'managed_money_long':long,'managed_money_short':short,'managed_money_net':net,'bias':'NET_LONG' if net is not None and net>0 else 'NET_SHORT' if net is not None and net<0 else 'UNCLEAR','note':'Weekly CFTC positioning context; not an intraday trigger.'}
        _cache_put('cftc:gold',out,_CACHE_TTLS['CFTC']); return out
    except Exception as e:
        stale,_=_cache_get('cftc:gold',allow_stale=True)
        return stale if stale is not None else {'status':'UNAVAILABLE','note':str(e)[:180]}

def build_market_context(mtf):
    usd=fetch_usd_context(); rates=fetch_rates_context(); cal=fetch_calendar_context(); sessions=build_session_level_context(mtf); volreg=build_volatility_regime(mtf); volume=build_volume_context(mtf); futures=fetch_optional_gold_futures(); vwap=build_vwap_context(mtf,futures); orderflow=build_orderflow_context(futures); cftc=fetch_cftc_gold_positioning()
    m5=(mtf.get('M5') or {}).get('metrics') or {}; h1=(mtf.get('H1') or {}).get('metrics') or {}; m15=(mtf.get('M15') or {}).get('metrics') or {}
    bull=0; bear=0; reasons=[]
    um=str(usd.get('momentum') or '')
    if um.startswith('BULLISH'): bear+=2; reasons.append('USD momentum is firm (gold headwind context)')
    elif um.startswith('BEARISH'): bull+=2; reasons.append('USD momentum is soft (gold tailwind context)')
    r10=(rates.get('series') or {}).get('US_10Y',{}).get('change')
    rr=(rates.get('series') or {}).get('US_10Y_REAL',{}).get('change')
    if isinstance(r10,(int,float)):
        if r10>0:bear+=1; reasons.append('10Y yield latest daily observation increased')
        elif r10<0:bull+=1; reasons.append('10Y yield latest daily observation decreased')
    if isinstance(rr,(int,float)):
        if rr>0:bear+=1; reasons.append('10Y real yield latest daily observation increased')
        elif rr<0:bull+=1; reasons.append('10Y real yield latest daily observation decreased')
    tech='MIXED'
    structs=[h1.get('structure'),m15.get('structure'),m5.get('structure')]
    if structs.count('HH_HL')>=2:tech='BULLISH'
    elif structs.count('LL_LH')>=2:tech='BEARISH'
    macro='BULLISH_GOLD' if bull>=bear+2 else 'BEARISH_GOLD' if bear>=bull+2 else 'MIXED'
    futures_public={k:v for k,v in futures.items() if k!='candles'}
    return {'usd':usd,'rates':rates,'calendar':cal,'sessions':sessions,'volatility_regime':volreg,'volume_context':volume,'gold_futures':futures_public,'vwap_context':vwap,'orderflow_context':orderflow,'cftc_positioning':cftc,'macro_bias':macro,'technical_alignment':tech,'bull_context_points':bull,'bear_context_points':bear,'reasons':reasons,'event_risk':cal.get('risk','UNKNOWN')}

def apply_market_context(mtf,ctx):
    """Context may rank/downweight existing zones; it never creates or moves a price zone."""
    m5=(mtf.get('M5') or {}).get('metrics') or {}; macro=ctx.get('macro_bias','MIXED'); event=ctx.get('event_risk','UNKNOWN')
    for side in ('buy','sell'):
        for z in ((m5.get('candidate_zones') or {}).get(side) or []):
            adj=0; why=[]
            if macro=='BULLISH_GOLD': adj=5 if side=='buy' else -4; why.append('macro context '+('supports' if side=='buy' else 'opposes'))
            elif macro=='BEARISH_GOLD': adj=5 if side=='sell' else -4; why.append('macro context '+('supports' if side=='sell' else 'opposes'))
            if event=='HIGH': adj-=8; why.append('high-impact event window')
            elif event=='ELEVATED': adj-=4; why.append('event-risk window')
            # V30: nearby established session/previous-day/week levels add only modest confluence.
            sess=ctx.get('sessions') or {}; atr=float(m5.get('atr14') or 1); zmid=(float(z.get('low'))+float(z.get('high')))/2
            near=[q for q in (sess.get('nearest_levels') or []) if abs(float(q.get('price'))-zmid)<=max(0.35,0.25*atr)]
            if near: adj+=3; why.append('near session/previous-day/week liquidity: '+str(near[0].get('name')))
            vr=(ctx.get('volatility_regime') or {}).get('regime')
            if vr=='EXTREME': adj-=4; why.append('extreme volatility regime')
            base=int(z.get('opportunity_score') or z.get('rank_score') or 0)
            z['pre_context_score']=base; z['context_adjustment']=adj; z['context_reasons']=why; z['opportunity_score']=max(0,min(100,base+adj))
        ((m5.get('candidate_zones') or {}).get(side) or []).sort(key=lambda x:(x.get('opportunity_score',0),x.get('rank_score',0)),reverse=True)
    m5['market_context']=ctx



def build_m1_pullback_state(m1):
    """V34.4: sensitive M1 pullback STATE detector, separate from point qualification.
    Detects a recent meaningful impulse followed by an opposite retracement using closed M1 candles.
    It never creates a point by itself.
    """
    c=(m1 or {}).get('latest_closed_candles') or []
    atr=float((m1 or {}).get('atr14') or 0)
    if len(c)<8 or atr<=0:
        return {'state':'NONE','direction':'NONE','market_state_detected':False,'note':'Not enough closed M1 data for pullback-state detection.'}
    cp=float((m1 or {}).get('data_current_price') or c[-1].get('c') or 0)
    start=max(0,len(c)-30); seg=c[start:]
    low_rel=min(range(len(seg)),key=lambda k:seg[k]['l']); high_rel=max(range(len(seg)),key=lambda k:seg[k]['h'])
    low_idx=start+low_rel; high_idx=start+high_rel; low_px=seg[low_rel]['l']; high_px=seg[high_rel]['h']

    bear_slice=c[max(start,low_idx-14):low_idx+1]
    bear_start=max(start,low_idx-14)+max(range(len(bear_slice)),key=lambda k:bear_slice[k]['h'])
    bear_imp=(c[bear_start]['h']-low_px)/atr
    bear_ret=max(0.0,(cp-low_px)/atr); bear_ratio=bear_ret/max(bear_imp,1e-9)

    bull_slice=c[max(start,high_idx-14):high_idx+1]
    bull_start=max(start,high_idx-14)+min(range(len(bull_slice)),key=lambda k:bull_slice[k]['l'])
    bull_imp=(high_px-c[bull_start]['l'])/atr
    bull_ret=max(0.0,(high_px-cp)/atr); bull_ratio=bull_ret/max(bull_imp,1e-9)

    # M1 should recognize the state early; point qualification remains stricter downstream.
    bear=(bear_start<low_idx and low_idx>=len(c)-10 and bear_imp>=1.05 and bear_ret>=0.15 and bear_ratio<=0.90)
    bull=(bull_start<high_idx and high_idx>=len(c)-10 and bull_imp>=1.05 and bull_ret>=0.15 and bull_ratio<=0.90)
    choose=None
    if bear and bull: choose='BEAR' if low_idx>high_idx else 'BULL'
    elif bear: choose='BEAR'
    elif bull: choose='BULL'
    if choose=='BEAR':
        return {'state':'PULLBACK_STARTING' if bear_ret<0.40 else 'PULLBACK_IN_PROGRESS','direction':'BEARISH_CONTINUATION','market_state_detected':True,'impulse_atr':round(bear_imp,2),'retracement_atr':round(bear_ret,2),'retracement_ratio':round(bear_ratio,2),'note':'Latest meaningful M1 impulse is bearish and an upward retracement is developing. This state does not create a SELL point by itself.'}
    if choose=='BULL':
        return {'state':'PULLBACK_STARTING' if bull_ret<0.40 else 'PULLBACK_IN_PROGRESS','direction':'BULLISH_CONTINUATION','market_state_detected':True,'impulse_atr':round(bull_imp,2),'retracement_atr':round(bull_ret,2),'retracement_ratio':round(bull_ratio,2),'note':'Latest meaningful M1 impulse is bullish and a downward retracement is developing. This state does not create a BUY point by itself.'}
    return {'state':'NONE','direction':'NONE','market_state_detected':False,'impulse_atr':0.0,'retracement_atr':0.0,'retracement_ratio':0.0,'note':'No meaningful active M1 pullback detected from closed candles.'}

def build_tpo_profile(candles, atr=None, lookback=180):
    """V36 time-at-price profile from closed M1 OHLC only. This is TPO/time acceptance, NOT volume profile."""
    rows=(candles or [])[-lookback:]
    if len(rows)<20:
        return {'status':'INSUFFICIENT_DATA','note':'Need more closed M1 candles for TPO profile.'}
    if not atr:
        ranges=[max(0.0001,float(x['h'])-float(x['l'])) for x in rows[-60:]]
        atr=statistics.median(ranges) if ranges else 1.0
    lo=min(float(x['l']) for x in rows); hi=max(float(x['h']) for x in rows)
    # Keep bins stable but fine enough to be useful on M1 Gold.
    step=max(float(atr)*0.22,(hi-lo)/80.0,0.05)
    n=max(8,min(120,int((hi-lo)/step)+1))
    step=(hi-lo)/max(1,n-1) if hi>lo else step
    bins=[0]*n
    for x in rows:
        a=float(x['l']); b=float(x['h'])
        i0=max(0,int((a-lo)/step)); i1=min(n-1,int((b-lo)/step))
        for i in range(i0,i1+1): bins[i]+=1
    total=sum(bins) or 1
    poc_i=max(range(n),key=lambda i:bins[i]); poc=lo+poc_i*step
    # 70% value area expanded from POC toward the more accepted adjacent bin.
    chosen={poc_i}; acc=bins[poc_i]; target=total*0.70; left=poc_i-1; right=poc_i+1
    while acc<target and (left>=0 or right<n):
        lv=bins[left] if left>=0 else -1; rv=bins[right] if right<n else -1
        if rv>lv: chosen.add(right); acc+=max(0,rv); right+=1
        else: chosen.add(left); acc+=max(0,lv); left-=1
    val=lo+min(chosen)*step; vah=lo+max(chosen)*step
    mx=max(bins) or 1
    hvn=[]; lvn=[]
    for i,v in enumerate(bins):
        price=lo+i*step
        if v>=mx*0.75: hvn.append(round(price,2))
        elif v<=mx*0.20: lvn.append(round(price,2))
    return {'status':'LIVE_DATA','type':'TPO_TIME_AT_PRICE','poc':round(poc,2),'vah':round(vah,2),'val':round(val,2),'bin_size':round(step,3),'bars':len(rows),'hvn':hvn[:8],'lvn':lvn[:8],'note':'Time-at-price profile from closed M1 candles; no volume is fabricated.'}

def build_initial_balance(candles):
    """V36 UTC session opening ranges / initial balance from closed M1 price data."""
    rows=candles or []
    if not rows: return {'status':'NO_DATA'}
    day=str(rows[-1].get('t',''))[:10]
    today=[x for x in rows if str(x.get('t',''))[:10]==day]
    def hour(x):
        try:return int(str(x.get('t','')).split(' ')[1].split(':')[0])
        except:return -1
    def rng(a,b):
        xs=[x for x in today if a<=hour(x)<b]
        if not xs:return None
        return {'high':round(max(float(x['h']) for x in xs),2),'low':round(min(float(x['l']) for x in xs),2),'bars':len(xs)}
    return {'status':'LIVE_DATA','date':day,'asia':rng(0,7),'london_opening_range':rng(7,8),'london_initial_balance':rng(7,8),'new_york_opening_range':rng(12,13),'new_york_initial_balance':rng(12,13),'note':'UTC price/time ranges only; they add context and never create a point.'}

def profile_session_context(side, lo, hi, tpo, ib, atr):
    """Small non-blocking location bonus for an already-created structural candidate."""
    bull=side=='buy'; mid=(lo+hi)/2.0; bonus=0; ev=[]
    if tpo.get('status')=='LIVE_DATA':
        val=float(tpo['val']); vah=float(tpo['vah']); poc=float(tpo['poc'])
        if bull and mid<=val+atr*.25: bonus+=3; ev.append('at/below TPO value low')
        elif (not bull) and mid>=vah-atr*.25: bonus+=3; ev.append('at/above TPO value high')
        if abs(mid-poc)<=atr*.25: ev.append('near TPO POC/acceptance')
        # LVN proximity can be useful as an edge/fast-travel reference, but only a tiny bonus.
        if any(abs(mid-float(x))<=atr*.20 for x in (tpo.get('lvn') or [])): bonus+=1; ev.append('near low-time node')
    for name in ('asia','london_opening_range','new_york_opening_range'):
        r=ib.get(name) if isinstance(ib,dict) else None
        if not r: continue
        level=float(r['low'] if bull else r['high'])
        if abs(mid-level)<=atr*.30: bonus+=2; ev.append('near '+name.replace('_',' ')); break
    return {'bonus':min(5,bonus),'evidence':ev}

def quantify_zone_reaction(candles, side, lo, hi, atr):
    """V36 closed-M1 acceptance/rejection measurement for a candidate after it is tested."""
    rows=(candles or [])[-30:]
    touched=[i for i,x in enumerate(rows) if float(x['l'])<=hi and float(x['h'])>=lo]
    if not touched:
        return {'state':'AHEAD','quality':'WAITING','penetration_pct':0,'closes_inside':0,'closes_beyond':0,'reclaim_bars':None,'displacement_atr':0,'note':'Point has not been tested by recent closed M1 candles.'}
    i=touched[0]; post=rows[i:]
    width=max(hi-lo,atr*.08,0.01)
    max_pen=0.0
    for x in post:
        if side=='buy': max_pen=max(max_pen,max(0.0,hi-float(x['l'])))
        else: max_pen=max(max_pen,max(0.0,float(x['h'])-lo))
    pen=min(200,100*max_pen/width)
    inside=sum(1 for x in post if lo<=float(x['c'])<=hi)
    beyond=sum(1 for x in post if (side=='buy' and float(x['c'])<lo) or (side=='sell' and float(x['c'])>hi))
    reclaim=None
    for j,x in enumerate(post):
        if (side=='buy' and float(x['c'])>hi) or (side=='sell' and float(x['c'])<lo): reclaim=j; break
    start=float(post[0]['c']); best=(max(float(x['h']) for x in post)-start) if side=='buy' else (start-min(float(x['l']) for x in post))
    disp=max(0,best)/(atr or 1)
    if beyond>=2: state='ACCEPTANCE_THROUGH'; quality='WEAK/INVALIDATING'
    elif reclaim is not None and reclaim<=3 and disp>=0.6: state='FAST_REJECTION_RECLAIM'; quality='STRONG'
    elif reclaim is not None: state='RECLAIM'; quality='MODERATE'
    else: state='TESTING'; quality='UNCONFIRMED'
    return {'state':state,'quality':quality,'penetration_pct':round(pen,0),'closes_inside':inside,'closes_beyond':beyond,'reclaim_bars':reclaim,'displacement_atr':round(disp,2),'note':'Closed-M1 measurement only. Rejection quality is context, not an automatic trade entry.'}

def v38_pullback_quality(m1, pullback_state):
    """Score the quality of a detected M1 pullback from closed OHLC only.
    This is context/ranking evidence, not a standalone signal or probability.
    """
    if not pullback_state.get('market_state_detected'):
        return {'score':0,'grade':'NONE','evidence':[],'retracement_ratio':0}
    c=(m1 or {}).get('latest_closed_candles') or []
    atr=float((m1 or {}).get('atr14') or 0) or 1.0
    ratio=float(pullback_state.get('retracement_ratio') or 0)
    impulse=float(pullback_state.get('impulse_atr') or 0)
    evidence=[]; score=0
    # Broad enough to preserve shallow and deep legitimate pullbacks; best score is not a hard gate.
    if 0.22 <= ratio <= 0.72: score+=24; evidence.append('balanced retracement depth')
    elif 0.12 <= ratio <= 0.86: score+=14; evidence.append('usable retracement depth')
    else: score+=5; evidence.append('extreme retracement depth')
    if impulse>=2.5: score+=22; evidence.append('strong preceding impulse')
    elif impulse>=1.5: score+=16; evidence.append('clear preceding impulse')
    else: score+=9
    recent=c[-8:]
    if recent:
        bodies=[abs(float(x['c'])-float(x['o'])) for x in recent]
        ranges=[max(0.0001,float(x['h'])-float(x['l'])) for x in recent]
        body_ratio=sum(bodies)/max(sum(ranges),1e-9)
        # Lower overlap/choppiness is better. Count adjacent range overlap.
        overlaps=[]
        for a,b in zip(recent,recent[1:]):
            inter=max(0.0,min(float(a['h']),float(b['h']))-max(float(a['l']),float(b['l'])))
            union=max(float(a['h']),float(b['h']))-min(float(a['l']),float(b['l']))
            overlaps.append(inter/max(union,1e-9))
        ov=sum(overlaps)/len(overlaps) if overlaps else 1.0
        if body_ratio>=0.52: score+=14; evidence.append('decisive candle bodies')
        elif body_ratio>=0.38: score+=9
        if ov<=0.38: score+=14; evidence.append('low candle overlap')
        elif ov<=0.58: score+=8
    st=str((m1 or {}).get('structure') or '')
    direction=str(pullback_state.get('direction') or '')
    if (direction=='BULLISH_CONTINUATION' and st=='HH_HL') or (direction=='BEARISH_CONTINUATION' and st=='LL_LH'):
        score+=16; evidence.append('protected trend structure intact')
    score=max(0,min(100,score))
    grade='STRONG' if score>=72 else 'GOOD' if score>=58 else 'MIXED' if score>=42 else 'WEAK'
    return {'score':score,'grade':grade,'evidence':evidence[:5],'retracement_ratio':round(ratio,2)}

def v38_refine_zone(m1, side, lo, hi, atr):
    """Compress a structural zone only when a smaller existing M1 FVG/OB overlaps it.
    No synthetic midpoint zone is created; otherwise original bounds are preserved.
    """
    originals=(lo,hi); options=[]
    for g in (m1.get('fvg_quality') or []):
        typ=str(g.get('type') or '')
        if (side=='buy' and typ!='BULLISH_FVG') or (side=='sell' and typ!='BEARISH_FVG'): continue
        try: a,b=float(g['low']),float(g['high'])
        except: continue
        x,y=max(lo,a),min(hi,b)
        if x<y: options.append((x,y,'FVG_OVERLAP'))
    for o in (m1.get('order_blocks') or []):
        typ=str(o.get('type') or ''); state=str(o.get('state') or '')
        if state=='BREAKER': continue
        if (side=='buy' and typ!='BULLISH_OB') or (side=='sell' and typ!='BEARISH_OB'): continue
        try: a,b=float(o['low']),float(o['high'])
        except: continue
        x,y=max(lo,a),min(hi,b)
        if x<y: options.append((x,y,'ORDER_BLOCK_OVERLAP'))
    if not options:
        return {'low':lo,'high':hi,'refined':False,'method':'ORIGINAL_STRUCTURE','compression_pct':0}
    # Prefer the narrowest genuine overlapping structural feature, but reject absurdly tiny slivers.
    minw=max(0.08*atr,0.03)
    options=[x for x in options if x[1]-x[0]>=minw] or options
    x,y,method=min(options,key=lambda q:q[1]-q[0])
    oldw=max(hi-lo,1e-9); neww=max(y-x,1e-9)
    return {'low':round(x,3),'high':round(y,3),'refined':neww<oldw*.92,'method':method,'compression_pct':round(max(0,100*(1-neww/oldw)))}

def v38_liquidity_target(m1, side, lo, hi, atr):
    """Map nearest exposed liquidity in the candidate's favorable direction and opposing liquidity behind it."""
    cp=float(m1.get('data_current_price') or 0); mid=(lo+hi)/2
    ext=m1.get('external_liquidity') or {}; internal=m1.get('internal_liquidity') or {}; path=m1.get('liquidity_path') or {}
    vals=[]
    keys=('swing_highs','equal_highs','minor_highs') if side=='buy' else ('swing_lows','equal_lows','minor_lows')
    for pack in (ext,internal):
        for k in keys:
            for v in (pack.get(k) or []):
                try: vals.append(float(v))
                except: pass
    pv=path.get('nearest_above' if side=='buy' else 'nearest_below')
    if isinstance(pv,(int,float)): vals.append(float(pv))
    vals=[v for v in vals if (v>mid if side=='buy' else v<mid)]
    target=(min(vals) if side=='buy' else max(vals)) if vals else None
    distance=(abs(target-mid)/atr) if target is not None and atr else None
    # Reward a visible objective far enough to justify travel, but never qualify a weak zone by itself.
    bonus=4 if distance is not None and distance>=1.0 else 2 if distance is not None and distance>=0.5 else 0
    return {'target':round(target,2) if target is not None else None,'distance_atr':round(distance,2) if distance is not None else None,'bonus':bonus,'note':'Nearest exposed liquidity in setup direction; objective/context only.'}


# ===== V39 PRECISION QUANT ENGINE =====
def v39_pullback_geometry(m1, pullback_state):
    """Quantify impulse/retracement geometry from closed M1 OHLC. Evidence only."""
    atr=float((m1 or {}).get('atr14') or 0) or 1.0
    ratio=float((pullback_state or {}).get('retracement_ratio') or 0)
    impulse=float((pullback_state or {}).get('impulse_atr') or 0)
    retr=float((pullback_state or {}).get('retracement_atr') or 0)
    rows=((m1 or {}).get('latest_closed_candles') or [])[-12:]
    overlaps=[]
    for a,b in zip(rows,rows[1:]):
        inter=max(0.0,min(float(a['h']),float(b['h']))-max(float(a['l']),float(b['l'])))
        union=max(float(a['h']),float(b['h']))-min(float(a['l']),float(b['l']))
        overlaps.append(inter/max(union,1e-9))
    overlap=sum(overlaps)/len(overlaps) if overlaps else 1.0
    score=0; ev=[]
    if 0.25<=ratio<=0.68: score+=30; ev.append('balanced impulse retracement')
    elif 0.12<=ratio<=0.82: score+=18; ev.append('usable impulse retracement')
    else: score+=6
    if impulse>=2.5: score+=25; ev.append('large impulse vs ATR')
    elif impulse>=1.5: score+=17; ev.append('clear impulse vs ATR')
    elif impulse>=1.05: score+=10
    if overlap<=0.38: score+=20; ev.append('clean low-overlap geometry')
    elif overlap<=0.58: score+=12
    if retr<=max(0.15,impulse*.75): score+=10
    st=str((m1 or {}).get('structure') or ''); d=str((pullback_state or {}).get('direction') or '')
    protected=(d=='BULLISH_CONTINUATION' and st=='HH_HL') or (d=='BEARISH_CONTINUATION' and st=='LL_LH')
    if protected: score+=15; ev.append('protected swing structure intact')
    score=max(0,min(100,score))
    return {'score':score,'retracement_ratio':round(ratio,3),'impulse_atr':round(impulse,2),'retracement_atr':round(retr,2),'overlap_ratio':round(overlap,2),'protected_structure':protected,'evidence':ev[:5]}

def v39_level_cluster(m1, side, lo, hi, atr):
    """Find a tight cluster of independent structural price families near a candidate."""
    mid=(lo+hi)/2; radius=max(atr*.55,(hi-lo)*.75,0.08); pts=[]
    def add(v,fam,label):
        try:v=float(v)
        except:return
        if abs(v-mid)<=radius: pts.append((v,fam,label))
    for g in (m1.get('fvg_quality') or []):
        typ=str(g.get('type') or '')
        if (side=='buy' and typ=='BULLISH_FVG') or (side=='sell' and typ=='BEARISH_FVG'):
            add(g.get('low'),'FVG','FVG edge'); add(g.get('high'),'FVG','FVG edge')
    for o in (m1.get('order_blocks') or []):
        typ=str(o.get('type') or '')
        if str(o.get('state') or '')!='BREAKER' and ((side=='buy' and typ=='BULLISH_OB') or (side=='sell' and typ=='BEARISH_OB')):
            add(o.get('low'),'OB','order-block edge'); add(o.get('high'),'OB','order-block edge')
    for v in (m1.get('last_swing_lows') or []) if side=='buy' else (m1.get('last_swing_highs') or []): add(v,'SWING','micro swing')
    dr=m1.get('dealing_range_hierarchy') or {}
    for k in ('micro','local','macro'):
        q=dr.get(k) or {}; add(q.get('equilibrium'),'RANGE_EQ',k+' equilibrium')
    if not pts:return {'score':0,'families':0,'levels':0,'cluster_low':None,'cluster_high':None,'width_atr':None,'evidence':[]}
    pts.sort(); best=[]
    window=max(atr*.28,0.05)
    for i,(v,_,_) in enumerate(pts):
        grp=[x for x in pts if abs(x[0]-v)<=window]
        fams=set(x[1] for x in grp)
        if (len(fams),len(grp))>(len(set(x[1] for x in best)),len(best)): best=grp
    fams=set(x[1] for x in best); low=min(x[0] for x in best); high=max(x[0] for x in best)
    width=max(high-low,0); score=min(18,len(fams)*5 + (3 if len(best)>=4 else 0))
    return {'score':score,'families':len(fams),'levels':len(best),'cluster_low':round(low,3),'cluster_high':round(high,3),'width_atr':round(width/atr,2) if atr else None,'evidence':sorted(set(x[2] for x in best))[:5]}

def v39_micro_refine(m1, side, lo, hi, atr, cluster):
    """Refine only inside the original structural zone and never below an ATR floor."""
    base=v38_refine_zone(m1,side,lo,hi,atr); x=float(base['low']); y=float(base['high']); method=base['method']
    cl, ch=cluster.get('cluster_low'),cluster.get('cluster_high')
    if isinstance(cl,(int,float)) and isinstance(ch,(int,float)):
        a=max(lo,float(cl)-atr*.10); b=min(hi,float(ch)+atr*.10)
        if a<b:
            x=max(x,a) if max(x,a)<min(y,b) else a; y=min(y,b) if max(x,a)<min(y,b) else b; method=method+'+MATH_CLUSTER'
    minw=max(atr*.12,0.04)
    if y-x<minw:
        c=(x+y)/2; x=max(lo,c-minw/2); y=min(hi,c+minw/2)
    old=max(hi-lo,1e-9)
    return {'low':round(x,3),'high':round(y,3),'refined':(y-x)<old*.92,'method':method,'compression_pct':round(max(0,100*(1-(y-x)/old))),'minimum_width_atr':0.12}

def v39_path_obstacles(m1, side, lo, hi, atr, target):
    """Count opposing structures between candidate midpoint and mapped liquidity target."""
    if not isinstance(target,(int,float)): return {'score_adjustment':0,'obstacles':0,'clean_path':False,'evidence':['no mapped target']}
    mid=(lo+hi)/2; a,b=sorted((mid,float(target))); obs=[]
    for g in (m1.get('fvg_quality') or []):
        typ=str(g.get('type') or '')
        opposing=(side=='buy' and typ=='BEARISH_FVG') or (side=='sell' and typ=='BULLISH_FVG')
        if opposing:
            gm=(float(g.get('low',0))+float(g.get('high',0)))/2
            if a<gm<b: obs.append('opposing FVG')
    for o in (m1.get('order_blocks') or []):
        typ=str(o.get('type') or '')
        opposing=(side=='buy' and typ=='BEARISH_OB') or (side=='sell' and typ=='BULLISH_OB')
        if opposing and str(o.get('state') or '')!='BREAKER':
            om=(float(o.get('low',0))+float(o.get('high',0)))/2
            if a<om<b: obs.append('opposing order block')
    adj=4 if not obs else -min(8,len(obs)*3)
    return {'score_adjustment':adj,'obstacles':len(obs),'clean_path':not obs,'evidence':obs[:4] or ['clean structural path to mapped liquidity']}

def v39_redundancy_adjust(source, seq_evidence, cluster):
    """Prevent one displacement family (BOS/FVG/OB) being counted as many independent confirmations."""
    fam=set()
    src=str(source)
    if 'FVG' in src: fam.add('DISPLACEMENT_FAMILY')
    if 'OB' in src: fam.add('DISPLACEMENT_FAMILY')
    for x in (seq_evidence or []):
        if x in ('MSS','BPR'): fam.add('DISPLACEMENT_FAMILY')
        elif x=='failed auction': fam.add('AUCTION')
        elif x=='nested range': fam.add('RANGE')
        elif x=='liquidity path': fam.add('LIQUIDITY')
    for x in (cluster.get('evidence') or []):
        if 'FVG' in x or 'order-block' in x: fam.add('DISPLACEMENT_FAMILY')
        elif 'swing' in x: fam.add('SWING')
        elif 'equilibrium' in x: fam.add('RANGE')
    independent=len(fam); penalty=0 if independent>=3 else 3 if independent==2 else 6
    return {'independent_families':independent,'families':sorted(fam),'penalty':penalty,'note':'Correlated BOS/FVG/OB-style evidence is grouped rather than double-counted.'}

def build_m1_pullback_bridge_candidates(m1, candles, pullback_state, pullback_quality):
    """V39.2 bridge from a detected M1 pullback to structural price candidates.

    This does NOT manufacture arbitrary levels. It re-scans the active M1 impulse/retracement
    for fresh structural locations that can be missed by the generic candidate pool:
    imbalance/FVG, last-opposite-candle displacement origin, broken micro support/resistance
    first retest, and retracement micro swings. Returned zones still pass the normal V39
    refinement, freshness, distance, competition and qualification logic downstream.
    """
    rows=(candles or [])[-90:]
    atr=float((m1 or {}).get('atr14') or 0)
    cp=float((m1 or {}).get('data_current_price') or (rows[-1].get('c') if rows else 0) or 0)
    direction=str((pullback_state or {}).get('direction') or '')
    qscore=int((pullback_quality or {}).get('score') or 0)
    if len(rows)<12 or atr<=0 or direction not in ('BEARISH_CONTINUATION','BULLISH_CONTINUATION') or qscore<55:
        return []

    side='SELL' if direction=='BEARISH_CONTINUATION' else 'BUY'
    # Reconstruct the latest impulse from closed M1 candles, using the same recency philosophy
    # as the pullback-state detector but with enough history to discover structural levels.
    start=max(0,len(rows)-55); seg=rows[start:]
    low_rel=min(range(len(seg)),key=lambda k:float(seg[k]['l']))
    high_rel=max(range(len(seg)),key=lambda k:float(seg[k]['h']))
    low_idx=start+low_rel; high_idx=start+high_rel
    if side=='SELL':
        sl=rows[max(start,low_idx-20):low_idx+1]
        if not sl: return []
        impulse_start=max(start,low_idx-20)+max(range(len(sl)),key=lambda k:float(sl[k]['h']))
        impulse_end=low_idx
    else:
        sl=rows[max(start,high_idx-20):high_idx+1]
        if not sl: return []
        impulse_start=max(start,high_idx-20)+min(range(len(sl)),key=lambda k:float(sl[k]['l']))
        impulse_end=high_idx
    if impulse_start>=impulse_end or impulse_end < len(rows)-14:
        return []

    out=[]; ztol=max(0.10,atr*0.16)
    def fresh(lo,hi,created_idx):
        # The active retracement may be approaching a level, but a bridge candidate must not
        # already have been materially traded through after its structural creation.
        after=rows[min(len(rows),created_idx+1):]
        touches=sum(1 for x in after if float(x['l'])<=hi and float(x['h'])>=lo)
        closes_through=sum(1 for x in after if (float(x['c'])>hi+0.08*atr if side=='SELL' else float(x['c'])<lo-0.08*atr))
        return touches<=1 and closes_through==0, touches
    def add(lo,hi,source,base,created_idx,evidence):
        lo=float(lo); hi=float(hi)
        if hi<lo: lo,hi=hi,lo
        # Continuation candidates must be ahead of the current retracement, not behind price.
        if side=='SELL' and lo<=cp: return
        if side=='BUY' and hi>=cp: return
        if ((lo-cp)/atr if side=='SELL' else (cp-hi)/atr)>5.5: return
        ok,touches=fresh(lo,hi,created_idx)
        if not ok:return
        out.append({'side':side,'low':round(lo,3),'high':round(hi,3),'source':source,
                    'rank_score':int(base),'touch_count':touches,'consumption':'UNTOUCHED' if touches==0 else 'LIGHT',
                    'pullback_bridge':True,'bridge_evidence':evidence,'created_index':created_idx})

    # 1) Impulse FVGs / imbalances. These are exact three-candle price gaps created by the leg.
    for i in range(max(2,impulse_start+2),min(len(rows),impulse_end+2)):
        a,b=rows[i-2],rows[i]
        if side=='SELL' and float(b['h'])<float(a['l']):
            add(float(b['h']),float(a['l']),'M1_PULLBACK_BEARISH_FVG',78,i,{'family':'FVG','impulse_index':i})
        elif side=='BUY' and float(b['l'])>float(a['h']):
            add(float(a['h']),float(b['l']),'M1_PULLBACK_BULLISH_FVG',78,i,{'family':'FVG','impulse_index':i})

    # 2) Last opposite candle before a >=1.0 ATR three-candle displacement inside the impulse.
    for i in range(max(1,impulse_start),max(1,impulse_end-1)):
        j=min(len(rows)-1,i+2); move=float(rows[j]['c'])-float(rows[i]['o'])
        aligned=(side=='SELL' and move<=-1.0*atr) or (side=='BUY' and move>=1.0*atr)
        if not aligned: continue
        for k in range(i-1,max(impulse_start-1,i-5),-1):
            x=rows[k]; opposite=(side=='SELL' and float(x['c'])>float(x['o'])) or (side=='BUY' and float(x['c'])<float(x['o']))
            if opposite:
                add(float(x['l']),float(x['h']),f'M1_PULLBACK_{side}_DISPLACEMENT_ORIGIN',80,k,{'family':'DISPLACEMENT_ORIGIN','move_atr':round(abs(move)/atr,2)})
                break

    # 3) Broken micro structure: first-retest of swing support/resistance broken by the impulse.
    def piv_low(i): return float(rows[i]['l'])<float(rows[i-1]['l']) and float(rows[i]['l'])<=float(rows[i+1]['l'])
    def piv_high(i): return float(rows[i]['h'])>float(rows[i-1]['h']) and float(rows[i]['h'])>=float(rows[i+1]['h'])
    search0=max(2,impulse_start-18)
    if side=='SELL':
        for i in range(search0,impulse_end):
            if not piv_low(i): continue
            level=float(rows[i]['l'])
            br=next((j for j in range(max(i+1,impulse_start),impulse_end+1) if float(rows[j]['c'])<level-0.03*atr),None)
            if br is not None: add(level-ztol,level+ztol,'M1_PULLBACK_BROKEN_SUPPORT_RETEST',84,br,{'family':'BROKEN_STRUCTURE','level':round(level,3)})
    else:
        for i in range(search0,impulse_end):
            if not piv_high(i): continue
            level=float(rows[i]['h'])
            br=next((j for j in range(max(i+1,impulse_start),impulse_end+1) if float(rows[j]['c'])>level+0.03*atr),None)
            if br is not None: add(level-ztol,level+ztol,'M1_PULLBACK_BROKEN_RESISTANCE_RETEST',84,br,{'family':'BROKEN_STRUCTURE','level':round(level,3)})

    # Deduplicate overlapping bridge zones while preserving the stronger structural source.
    ded=[]
    for z in sorted(out,key=lambda x:x['rank_score'],reverse=True):
        if not any(not (z['high']<q['low']-0.08*atr or z['low']>q['high']+0.08*atr) for q in ded):
            ded.append(z)
    return ded[:8]

def v393_price_action_sequence(candles, side, lo, hi, atr):
    """Closed-M1 price-action sequence around a candidate. Supportive only; never creates a zone."""
    if not candles or atr <= 0:
        return {'stage':0,'max_stage':5,'state':'WAITING','steps':{},'note':'M1 candles unavailable.'}
    side=str(side).lower(); recent=candles[-24:]
    touch_i=next((i for i,x in enumerate(recent) if float(x['l'])<=hi and float(x['h'])>=lo),None)
    if touch_i is None:
        cp=float(recent[-1]['c']); dist=max(0,cp-hi) if side=='buy' else max(0,lo-cp)
        return {'stage':0,'max_stage':5,'state':'APPROACHING' if dist<=atr*1.5 else 'AHEAD','steps':{'sweep':False,'rejection_reclaim':False,'displacement':False,'micro_structure_break':False,'follow_through':False},'distance_atr':round(dist/atr,2),'note':'Waiting for closed-M1 interaction.'}
    pre=recent[max(0,touch_i-6):touch_i+1]; post=recent[touch_i:]
    x=recent[touch_i]; o,h,l,c=map(float,(x['o'],x['h'],x['l'],x['c']))
    prev_lows=[float(q['l']) for q in pre[:-1]]; prev_highs=[float(q['h']) for q in pre[:-1]]
    if side=='buy':
        sweep=bool(prev_lows) and l < min(prev_lows) and c > min(prev_lows)
        rejection=(l<=hi and c>=lo and c>(l+(h-l)*0.45))
        disp=any(float(q['c'])-float(q['o']) >= atr*.55 for q in post[:4])
        ref=max(prev_highs[-3:] or [h]); brk=any(float(q['c'])>ref for q in post[1:6])
        ft=sum(1 for q in post[1:5] if float(q['c'])>float(q['o']))>=2
    else:
        sweep=bool(prev_highs) and h > max(prev_highs) and c < max(prev_highs)
        rejection=(h>=lo and c<=hi and c<(l+(h-l)*0.55))
        disp=any(float(q['o'])-float(q['c']) >= atr*.55 for q in post[:4])
        ref=min(prev_lows[-3:] or [l]); brk=any(float(q['c'])<ref for q in post[1:6])
        ft=sum(1 for q in post[1:5] if float(q['c'])<float(q['o']))>=2
    steps={'sweep':sweep,'rejection_reclaim':rejection,'displacement':disp,'micro_structure_break':brk,'follow_through':ft}
    # Ordered stage: later evidence cannot skip missing earlier reaction evidence.
    ordered=[sweep or rejection,rejection,disp,brk,ft]; stage=0
    for ok in ordered:
        if ok: stage+=1
        else: break
    state='CONFIRMED' if stage>=5 else 'DEVELOPING' if stage>=2 else 'EARLY_REACTION' if stage==1 else 'TESTING'
    return {'stage':stage,'max_stage':5,'state':state,'steps':steps,'note':'Sequence is reaction evidence, not an automatic entry.'}

def v393_trap_failure(candles, side, lo, hi, atr):
    """Detect closed-M1 acceptance through a zone and failed reclaim / opposite transition evidence."""
    if not candles or atr<=0:return {'state':'NONE','opposite_transition':False}
    side=str(side).lower(); r=candles[-16:]
    touched=any(float(x['l'])<=hi and float(x['h'])>=lo for x in r)
    if not touched:return {'state':'NONE','opposite_transition':False}
    if side=='buy':
        beyond=[i for i,x in enumerate(r) if float(x['c']) < lo]
        if not beyond:return {'state':'HOLDING_OR_UNRESOLVED','opposite_transition':False}
        i=beyond[-1]; after=r[i+1:]
        reclaimed=any(float(x['c'])>hi for x in after)
        opp_disp=any(float(x['o'])-float(x['c'])>=atr*.55 for x in r[max(0,i-2):])
        failed=not reclaimed and opp_disp
        return {'state':'BEARISH_TRAP_TRANSITION' if failed else 'ACCEPTANCE_BELOW' if not reclaimed else 'RECLAIMED','opposite_transition':failed,'acceptance_side':'BELOW'}
    beyond=[i for i,x in enumerate(r) if float(x['c']) > hi]
    if not beyond:return {'state':'HOLDING_OR_UNRESOLVED','opposite_transition':False}
    i=beyond[-1]; after=r[i+1:]
    reclaimed=any(float(x['c'])<lo for x in after)
    opp_disp=any(float(x['c'])-float(x['o'])>=atr*.55 for x in r[max(0,i-2):])
    failed=not reclaimed and opp_disp
    return {'state':'BULLISH_TRAP_TRANSITION' if failed else 'ACCEPTANCE_ABOVE' if not reclaimed else 'RECLAIMED','opposite_transition':failed,'acceptance_side':'ABOVE'}

def v394_compression_expansion(candles, atr):
    """Closed-M1 compression/expansion classifier. Context only; never creates a zone."""
    if not candles or len(candles)<14 or atr<=0:
        return {'state':'UNAVAILABLE','score':0,'note':'Not enough M1 candles.'}
    r=candles[-12:]
    ranges=[max(0.0,float(x['h'])-float(x['l'])) for x in r]
    bodies=[abs(float(x['c'])-float(x['o'])) for x in r]
    recent=sum(ranges[-4:])/4; prior=sum(ranges[:8])/8
    overlap=0
    for a,b in zip(r[-6:-1],r[-5:]):
        if min(float(a['h']),float(b['h'])) >= max(float(a['l']),float(b['l'])): overlap+=1
    last=max(ranges[-1],1e-9); body=bodies[-1]
    contraction=recent/max(prior,1e-9)
    expansion=last/max(prior,1e-9)
    if expansion>=1.65 and body/max(last,1e-9)>=0.62:
        state='EXPANSION'; score=min(100,round(55+25*(expansion-1.0)))
    elif contraction<=0.72 and overlap>=3:
        state='COMPRESSION'; score=min(100,round(55+45*(1-contraction)))
    elif overlap>=4:
        state='RANGE_COMPRESSION'; score=60
    else:
        state='NORMAL'; score=45
    return {'state':state,'score':score,'range_ratio':round(contraction,2),'last_range_atr':round(last/atr,2),'overlap_count':overlap,'note':'M1 range/overlap context only; it does not create or veto a point.'}

def v394_market_regime(m1, candles, atr, compression):
    """M1 Regime 2.0: descriptive context for setup ranking/diagnostics, not a direction gate."""
    st=str(m1.get('structure') or 'UNCLEAR'); mom=str(m1.get('momentum') or 'NEUTRAL')
    shock=str(m1.get('shock_detector') or '')=='TRIGGERED'
    ce=str((compression or {}).get('state') or 'NORMAL')
    if shock or ce=='EXPANSION': regime='EXPANSION_VOLATILITY_SHOCK'
    elif ce in ('COMPRESSION','RANGE_COMPRESSION'): regime='COMPRESSION'
    elif st in ('HH_HL','LL_LH') and ('STRONG' in mom): regime='TRENDING'
    elif st in ('HH_HL','LL_LH'): regime='ORDERLY_TREND_OR_PULLBACK'
    elif st in ('MIXED','UNCLEAR') and ce=='NORMAL': regime='RANGE_OR_TRANSITION'
    else: regime='TRANSITION'
    return {'regime':regime,'structure':st,'momentum':mom,'compression_state':ce,'note':'Regime changes context/ranking diagnostics only; M1 structure still owns point generation.'}

def v393_setup_state(candles, side, lo, hi, atr, pa, trap, reaction=None):
    """V39.4 state-integrity lifecycle. Invalidated originals stay invalidated; later reclaim is a new state."""
    if not candles:return {'state':'FORMING','original_state':'FORMING','note':'Waiting for M1 data.'}
    cp=float(candles[-1]['c']); side=str(side).lower(); reaction=reaction or {}
    touched=any(float(x['l'])<=hi and float(x['h'])>=lo for x in candles[-24:])
    accepted_through=str(reaction.get('state') or '')=='ACCEPTANCE_THROUGH' or int(reaction.get('closes_beyond') or 0)>=2
    reclaimed=str(trap.get('state') or '')=='RECLAIMED'
    if trap.get('opposite_transition'):
        state='FAILED_TRAP_TRANSITION'; original='INVALIDATED'
    elif accepted_through and reclaimed:
        state='RECLAIM_AFTER_INVALIDATION'; original='INVALIDATED'
    elif accepted_through:
        state='INVALIDATED'; original='INVALIDATED'
    elif pa.get('state')=='CONFIRMED':
        state='STRUCTURE_CONFIRMED'; original='ACTIVE'
    elif pa.get('stage',0)>=3:
        state='CONFIRMING'; original='ACTIVE'
    elif pa.get('stage',0)>=1:
        state='REJECTING'; original='ACTIVE'
    elif touched:
        state='TESTING'; original='ACTIVE'
    else:
        dist=max(0,cp-hi) if side=='buy' else max(0,lo-cp)
        state='APPROACHING' if dist<=atr*1.5 else 'CANDIDATE_FOUND'; original='FRESH'
    return {'state':state,'original_state':original,'price':round(cp,2),'reclaim_is_new_setup':state=='RECLAIM_AFTER_INVALIDATION','note':'Original invalidation is never erased by a later reclaim; reclaim is tracked as a new setup state.'}



def v395_extra_m1_candidates(m1, candles, pullback_state):
    """Independent M1 candidate routes for V39.5.

    Adds only price-derived areas: first break/retest levels and transition/reversal
    retest areas. These are candidate generators, not automatic trade signals.
    """
    rows=(candles or [])[-100:]
    atr=float((m1 or {}).get('atr14') or 0)
    cp=float((m1 or {}).get('data_current_price') or (rows[-1].get('c') if rows else 0) or 0)
    if len(rows)<18 or atr<=0:return []
    out=[]; tol=max(.08,atr*.12)
    def add(side,lo,hi,source,base,idx,evidence):
        lo,hi=sorted((float(lo),float(hi)))
        # Candidate must still be ahead of the latest closed price.
        if side=='BUY' and hi>=cp:return
        if side=='SELL' and lo<=cp:return
        if ((cp-hi)/atr if side=='BUY' else (lo-cp)/atr)>5.5:return
        after=rows[min(len(rows),idx+1):]
        touches=sum(1 for x in after if float(x['l'])<=hi and float(x['h'])>=lo)
        closes=sum(1 for x in after if (float(x['c'])<lo-.08*atr if side=='BUY' else float(x['c'])>hi+.08*atr))
        if touches>1 or closes:return
        out.append({'side':side,'low':round(lo,3),'high':round(hi,3),'source':source,'rank_score':base,
                    'touch_count':touches,'consumption':'UNTOUCHED' if touches==0 else 'LIGHT',
                    'v395_route':evidence.get('route'),'v395_evidence':evidence,'created_index':idx})
    # BREAK & RETEST: a close decisively through a recent 5-bar extreme creates a first-retest level.
    for i in range(7,len(rows)-2):
        prev=rows[i-6:i]
        ph=max(float(x['h']) for x in prev); pl=min(float(x['l']) for x in prev)
        c=float(rows[i]['c']); o=float(rows[i]['o'])
        body=abs(c-o)
        if c>ph+.05*atr and body>=.35*atr:
            add('BUY',ph-tol,ph+tol,'M1_BREAK_RETEST_BUY',74,i,{'route':'BREAK_RETEST','break_index':i,'level':round(ph,3)})
        if c<pl-.05*atr and body>=.35*atr:
            add('SELL',pl-tol,pl+tol,'M1_BREAK_RETEST_SELL',74,i,{'route':'BREAK_RETEST','break_index':i,'level':round(pl,3)})
    # TRANSITION: sweep an extreme, reclaim it, then opposite displacement. Candidate is first retest
    # of the reclaimed micro level; this is deliberately separate from continuation pullback logic.
    for i in range(8,len(rows)-2):
        prior=rows[i-7:i]
        ph=max(float(x['h']) for x in prior); pl=min(float(x['l']) for x in prior)
        x=rows[i]; n=rows[i+1]
        # bullish: sell-side sweep + reclaim + bullish displacement
        if float(x['l'])<pl-.05*atr and float(x['c'])>pl and float(n['c'])>float(n['o']) and (float(n['c'])-float(n['o']))>=.45*atr:
            add('BUY',pl-tol,pl+tol,'M1_TRANSITION_RECLAIM_BUY',76,i+1,{'route':'TRANSITION','sweep':'SELL_SIDE','reclaim':round(pl,3)})
        # bearish reverse
        if float(x['h'])>ph+.05*atr and float(x['c'])<ph and float(n['c'])<float(n['o']) and (float(n['o'])-float(n['c']))>=.45*atr:
            add('SELL',ph-tol,ph+tol,'M1_TRANSITION_RECLAIM_SELL',76,i+1,{'route':'TRANSITION','sweep':'BUY_SIDE','reclaim':round(ph,3)})
    # Deduplicate overlapping same-side areas, preferring newest / higher base score.
    out.sort(key=lambda z:(z['rank_score'],z['created_index']),reverse=True)
    kept=[]
    for z in out:
        if any(k['side']==z['side'] and not (z['high']<k['low']-.15*atr or z['low']>k['high']+.15*atr) for k in kept):continue
        kept.append(z)
    return kept[:10]

def build_m1_precision_engine(mtf, vwap_context=None):
    """V39.1 M1-FIRST precision generator.
    M1 owns setup detection, candidate generation, qualification and precision ranking.
    M5/M15/H1 keep their full structure/concept analysis but act only as non-blocking
    context/confluence. Higher-timeframe disagreement can warn or adjust final ranking;
    it cannot delete an otherwise legitimate M1 precision candidate.
    """
    m1=(mtf.get('M1') or {}).get('metrics') or {}
    m5=(mtf.get('M5') or {}).get('metrics') or {}
    m15=(mtf.get('M15') or {}).get('metrics') or {}
    h1=(mtf.get('H1') or {}).get('metrics') or {}
    if not m1:
        return {'state':'UNAVAILABLE','direction':'NONE','context_score':0,'candidates':[],'note':'M1 data unavailable.'}

    def side_bias(m):
        st=str(m.get('structure') or 'UNCLEAR'); mom=str(m.get('momentum') or 'NEUTRAL'); pr=str(m.get('current_pressure') or 'NEUTRAL')
        b=s=0
        if st=='HH_HL': b+=24
        elif st=='LL_LH': s+=24
        if mom.startswith('BULLISH'): b+=18 if 'STRONG' in mom else 12
        elif mom.startswith('BEARISH'): s+=18 if 'STRONG' in mom else 12
        if 'BULLISH' in pr: b+=10
        elif 'BEARISH' in pr: s+=10
        ev=str(m.get('structure_event') or '')
        if 'BULLISH' in ev: b+=12
        elif 'BEARISH' in ev: s+=12
        return b,s

    b5,s5=side_bias(m5); b15,s15=side_bias(m15); b1h,s1h=side_bias(h1); bm1,sm1=side_bias(m1)
    trans=m5.get('transition_engine') or {}; tstate=str(trans.get('state') or '')
    if 'BULLISH' in tstate: b5+=min(22,int(trans.get('bullish_score') or 0)//4)
    if 'BEARISH' in tstate: s5+=min(22,int(trans.get('bearish_score') or 0)//4)

    # V39.1: higher timeframes describe the environment only. They do NOT set M1
    # qualification thresholds and they never veto an M1 candidate.
    bull_context=b5 + int(b15*0.45) + int(b1h*0.20)
    bear_context=s5 + int(s15*0.45) + int(s1h*0.20)
    context_direction='BULLISH' if bull_context>=50 and bull_context>=bear_context+6 else 'BEARISH' if bear_context>=50 and bear_context>=bull_context+6 else 'MIXED'
    shock=str(m5.get('shock_detector') or '')=='TRIGGERED'

    cp=float(m1.get('data_current_price') or m5.get('data_current_price') or 0); atr=float(m1.get('atr14') or 1)
    allowed_by_side={
        'buy':{'BULLISH_FVG','BULLISH_OB','SWING_DEMAND','DYNAMIC_BROKEN_RESISTANCE_RETEST',
               'M1_PULLBACK_BULLISH_FVG','M1_PULLBACK_BUY_DISPLACEMENT_ORIGIN','M1_PULLBACK_BROKEN_RESISTANCE_RETEST',
               'M1_BREAK_RETEST_BUY','M1_TRANSITION_RECLAIM_BUY'},
        'sell':{'BEARISH_FVG','BEARISH_OB','SWING_SUPPLY','DYNAMIC_BROKEN_SUPPORT_RETEST',
                'M1_PULLBACK_BEARISH_FVG','M1_PULLBACK_SELL_DISPLACEMENT_ORIGIN','M1_PULLBACK_BROKEN_SUPPORT_RETEST',
                'M1_BREAK_RETEST_SELL','M1_TRANSITION_RECLAIM_SELL'}
    }
    m1st=str(m1.get('structure') or 'UNCLEAR'); m1mom=str(m1.get('momentum') or 'NEUTRAL'); m1ev=str(m1.get('structure_event') or '')
    pullback_state=build_m1_pullback_state(m1)
    pullback_quality=v38_pullback_quality(m1,pullback_state)
    pullback_geometry=v39_pullback_geometry(m1,pullback_state)
    m1_candles=(mtf.get('M1') or {}).get('candles') or []
    compression_expansion=v394_compression_expansion(m1_candles,atr)
    market_regime_v2=v394_market_regime(m1,m1_candles,atr,compression_expansion)
    pullback_bridge=build_m1_pullback_bridge_candidates(m1,m1_candles,pullback_state,pullback_quality)
    extra_routes=v395_extra_m1_candidates(m1,m1_candles,pullback_state)
    diagnostics={'raw':0,'fresh':0,'distance_ok':0,'ranked':0,'qualified':0,'watch':0,'rejected':{},'by_route':{}}
    tpo=build_tpo_profile(m1_candles,atr)
    initial_balance=build_initial_balance(m1_candles)
    rows=[]
    ranked_pool=[]
    vw=vwap_context or {}
    daily_vw=((vw.get('daily') or {}).get('vwap'))
    session_vw=((vw.get('session') or {}).get('vwap'))
    avpack=vw.get('avwap') or {}
    bull_av=((avpack.get('bullish') or {}).get('vwap'))
    bear_av=((avpack.get('bearish') or {}).get('vwap'))
    for side in ('buy','sell'):
        bull=side=='buy'; own_bias=bm1 if bull else sm1; opp_bias=sm1 if bull else bm1
        micro_align=(bull and (m1st=='HH_HL' or m1mom.startswith('BULLISH') or 'BULLISH' in m1ev)) or ((not bull) and (m1st=='LL_LH' or m1mom.startswith('BEARISH') or 'BEARISH' in m1ev))
        event_align=(bull and 'BULLISH' in m1ev) or ((not bull) and 'BEARISH' in m1ev)
        momentum_align=(bull and m1mom.startswith('BULLISH')) or ((not bull) and m1mom.startswith('BEARISH'))
        strong_micro = micro_align and (event_align or 'STRONG' in m1mom or own_bias>=36)
        context_aligned=(context_direction=='BULLISH' and bull) or (context_direction=='BEARISH' and not bull)
        # Point family is now decided by M1 itself, not by M5/HTF direction.
        pbdir=str(pullback_state.get('direction') or '')
        m1_continuation=(bull and pbdir=='BULLISH_CONTINUATION') or ((not bull) and pbdir=='BEARISH_CONTINUATION')
        point_class='M1_PRECISION_CONTINUATION' if m1_continuation else 'M1_PRECISION_TRANSITION'
        # One M1-owned qualification floor. HTF alignment cannot raise/lower this gate.
        min_score=66
        # V39.5: lack of same-direction M1 momentum no longer deletes a legitimate
        # transition/break-retest candidate before it can be evaluated. It is reflected
        # in scoring and WATCH/QUALIFIED state instead.

        native_pool=list(((m1.get('candidate_zones') or {}).get(side) or []))
        bridge_pool=[z for z in pullback_bridge if str(z.get('side') or '').lower()==side]
        route_pool=[z for z in extra_routes if str(z.get('side') or '').lower()==side]
        candidate_pool=native_pool+bridge_pool+route_pool
        diagnostics['raw'] += len(candidate_pool)
        for _z in candidate_pool:
            _r=_z.get('v395_route') or ('PULLBACK_BRIDGE' if _z.get('pullback_bridge') else 'NATIVE')
            diagnostics['by_route'][_r]=diagnostics['by_route'].get(_r,0)+1
        for z in candidate_pool:
            src=str(z.get('source') or '')
            if src not in allowed_by_side[side]:
                diagnostics['rejected']['SOURCE_NOT_ALLOWED']=diagnostics['rejected'].get('SOURCE_NOT_ALLOWED',0)+1; continue
            lo=float(z.get('low')); hi=float(z.get('high')); touches=int(z.get('touch_count') or 0); cons=str(z.get('consumption') or '').upper()
            original_lo,original_hi=lo,hi
            math_cluster=v39_level_cluster(m1,side,lo,hi,atr)
            refinement=v39_micro_refine(m1,side,lo,hi,atr,math_cluster)
            lo,hi=float(refinement['low']),float(refinement['high'])
            ahead=(hi < cp) if bull else (lo > cp)
            if not ahead:
                diagnostics['rejected']['NOT_AHEAD']=diagnostics['rejected'].get('NOT_AHEAD',0)+1; continue
            if touches>1:
                diagnostics['rejected']['TOO_MANY_TOUCHES']=diagnostics['rejected'].get('TOO_MANY_TOUCHES',0)+1; continue
            if cons not in ('','UNTOUCHED','LIGHT'):
                diagnostics['rejected']['CONSUMED']=diagnostics['rejected'].get('CONSUMED',0)+1; continue
            diagnostics['fresh'] += 1
            dist=max(0,cp-hi) if bull else max(0,lo-cp); datr=dist/atr if atr else 99
            if datr>5.5:
                diagnostics['rejected']['TOO_FAR']=diagnostics['rejected'].get('TOO_FAR',0)+1; continue
            diagnostics['distance_ok'] += 1
            base=int(z.get('rank_score') or 0)
            source_bonus=13 if src.startswith('M1_BREAK_RETEST_') else 12 if src.startswith('M1_TRANSITION_RECLAIM_') else 13 if src.startswith('M1_PULLBACK_BROKEN_') else 12 if src.startswith('DYNAMIC_BROKEN_') else 11 if src.startswith('M1_PULLBACK_') and src.endswith('_FVG') else 10 if src.endswith('_FVG') else 10 if 'DISPLACEMENT_ORIGIN' in src else 8 if src.endswith('_OB') else 5
            micro_bonus=14 if strong_micro else 9 if micro_align else 3
            proximity=max(0,12-int(datr*3))
            # HTF is deliberately excluded from M1 structural qualification.
            context_bonus=0
            pullback_bonus=6 if m1_continuation else 0
            ind=inducement_relationship(m1,side,z,atr)
            inducement_bonus=int(ind.get('bonus') or 0)
            # V34.6 M1 sequence intelligence: supportive bonuses only, never mandatory.
            seq_bonus=0; seq_ev=[]
            mss=str(m1.get('market_structure_shift') or 'NONE'); auc=str(m1.get('auction_state') or '')
            dr=m1.get('dealing_range_hierarchy') or {}; micro_pd=((dr.get('micro') or {}).get('state'))
            lp=m1.get('liquidity_path') or {}; bprs=m1.get('balanced_price_ranges') or []
            if (bull and mss=='BULLISH_MSS') or ((not bull) and mss=='BEARISH_MSS'): seq_bonus+=5; seq_ev.append('MSS')
            if (bull and auc=='FAILED_AUCTION_BELOW') or ((not bull) and auc=='FAILED_AUCTION_ABOVE'): seq_bonus+=4; seq_ev.append('failed auction')
            if (bull and micro_pd=='DISCOUNT') or ((not bull) and micro_pd=='PREMIUM'): seq_bonus+=3; seq_ev.append('nested range')
            if any(not (hi<float(r['low'])-atr*.2 or lo>float(r['high'])+atr*.2) for r in bprs): seq_bonus+=3; seq_ev.append('BPR')
            if isinstance(lp.get('nearest_above' if bull else 'nearest_below'),(int,float)): seq_bonus+=2; seq_ev.append('liquidity path')
            ps=profile_session_context(side,lo,hi,tpo,initial_balance,atr)
            pb_quality_bonus=min(8,int(pullback_quality.get('score') or 0)//10) if pullback_bonus else 0
            liquidity_target=v38_liquidity_target(m1,side,lo,hi,atr)
            path_quality=v39_path_obstacles(m1,side,lo,hi,atr,liquidity_target.get('target'))
            redundancy=v39_redundancy_adjust(src,seq_ev,math_cluster)
            geometry_bonus=min(8,int(pullback_geometry.get('score') or 0)//12) if pullback_bonus else 0
            cluster_bonus=min(12,int(math_cluster.get('score') or 0))
            structural_score=max(0,min(100,base+source_bonus+micro_bonus+proximity+context_bonus+pullback_bonus+pb_quality_bonus+geometry_bonus+cluster_bonus+inducement_bonus+min(12,seq_bonus)+int(path_quality.get('score_adjustment') or 0)-int(redundancy.get('penalty') or 0)))

            # HTF CONFLUENCE (NON-BLOCKING): M5/M15/H1 keep all their own concepts and
            # candidate zones. Overlap/proximity can modestly improve final competition
            # ranking, while conflict is shown as context only. It never changes the M1
            # structural score or qualification threshold.
            htf_hits=[]
            htf_weights={'M5':3,'M15':2,'H1':1}
            for tf,tm in (('M5',m5),('M15',m15),('H1',h1)):
                for hz in (((tm.get('candidate_zones') or {}).get(side)) or []):
                    try:
                        hlo,hhi=float(hz.get('low')),float(hz.get('high'))
                    except (TypeError,ValueError):
                        continue
                    tol_htf=max(atr*.75,0.25)
                    if not (hi < hlo-tol_htf or lo > hhi+tol_htf):
                        htf_hits.append({'timeframe':tf,'source':str(hz.get('source') or 'STRUCTURE'),'low':round(hlo,2),'high':round(hhi,2),'weight':htf_weights[tf]})
                        break
            htf_confluence_bonus=min(6,sum(x['weight'] for x in htf_hits))
            mtf_alignment='ALIGNED' if context_aligned else 'MIXED' if context_direction=='MIXED' else 'COUNTER_CONTEXT'
            mtf_context_adjustment=4 if context_aligned else 0 if context_direction=='MIXED' else -2
            # V37.1 candidate pool: keep weak/random zones out, but let legitimate near-qualified
            # structures reach location ranking before the final qualification threshold.
            if structural_score < max(52, min_score-14):
                continue
            tol=max(atr*.50,0.20)
            side_av=bull_av if bull else bear_av
            locs=[('DAILY_VWAP',daily_vw),('SESSION_VWAP',session_vw),('AVWAP',side_av)]
            available=[(n,float(v)) for n,v in locs if isinstance(v,(int,float))]
            near=[n for n,v in available if lo-tol <= v <= hi+tol]
            vwap_bonus=0
            if 'DAILY_VWAP' in near: vwap_bonus += 3
            if 'SESSION_VWAP' in near: vwap_bonus += 4
            if 'AVWAP' in near: vwap_bonus += 5
            vwap_bonus=min(10,vwap_bonus)
            if near:
                vwstate='SUPPORTIVE'
            elif not available:
                vwstate='UNAVAILABLE'
            else:
                adverse=all((v < lo-tol if bull else v > hi+tol) for _,v in available)
                vwstate='CONFLICTING' if adverse else 'NEUTRAL'
                if adverse: vwap_bonus=-2
            depth='SHALLOW' if datr<=1.5 else 'INTERMEDIATE' if datr<=3.25 else 'DEEP'
            rank_score=max(0,min(100,structural_score+int(ps.get('bonus') or 0)+int(liquidity_target.get('bonus') or 0)+vwap_bonus+htf_confluence_bonus+mtf_context_adjustment))
            reaction=quantify_zone_reaction(m1_candles,side,lo,hi,atr)
            pa_sequence=v393_price_action_sequence(m1_candles,side,lo,hi,atr)
            trap_failure=v393_trap_failure(m1_candles,side,lo,hi,atr)
            setup_lifecycle=v393_setup_state(m1_candles,side,lo,hi,atr,pa_sequence,trap_failure,reaction)
            route=z.get('v395_route') or ('PULLBACK_CONTINUATION' if z.get('pullback_bridge') or m1_continuation else 'NATIVE_STRUCTURE')
            local_point_class='M1_PRECISION_BREAK_RETEST' if route=='BREAK_RETEST' else 'M1_PRECISION_TRANSITION' if route=='TRANSITION' else point_class
            mode='BREAK_RETEST' if route=='BREAK_RETEST' else 'TRANSITION' if route=='TRANSITION' else ('CONTINUATION' if local_point_class.endswith('CONTINUATION') else 'TRANSITION')
            item={'side':side.upper(),'low':round(lo,2),'high':round(hi,2),'source':src,'score':rank_score,'structural_score':structural_score,'ranking_score':rank_score,'gate_score':max(bull_context,bear_context),'context_score':bull_context if bull else bear_context,'distance_m1_atr':round(datr,2),'depth':depth,'original_zone':{'low':round(original_lo,2),'high':round(original_hi,2)},'zone_refinement':refinement,'pullback_quality':pullback_quality,'pullback_geometry':pullback_geometry,'mathematical_cluster':math_cluster,'liquidity_target':liquidity_target,'path_obstacles':path_quality,'evidence_redundancy':redundancy,'m1_structure':m1st,'m1_momentum':m1mom,'m1_event':m1ev,'point_class':local_point_class,'mode':mode,'candidate_route':route,'context_direction':context_direction,'mtf_alignment':mtf_alignment,'htf_confluence':{'bonus':htf_confluence_bonus,'hits':htf_hits,'non_blocking':True},'inducement_context':ind,'sequence_context':{'bonus':min(12,seq_bonus),'evidence':seq_ev},'profile_session_context':ps,'acceptance_rejection':reaction,'price_action_sequence':pa_sequence,'setup_lifecycle':setup_lifecycle,'trap_failure':trap_failure,'compression_expansion':compression_expansion,'market_regime_v2':market_regime_v2,'vwap_context':vwstate,'avwap_context':'SUPPORTIVE' if 'AVWAP' in near else 'UNAVAILABLE' if not isinstance(side_av,(int,float)) else 'NEUTRAL','vwap_ranking_bonus':vwap_bonus,'pullback_bridge':bool(z.get('pullback_bridge')),'bridge_evidence':z.get('bridge_evidence') or {},'vwap_detail':{'daily_vwap':daily_vw,'session_vwap':session_vw,'avwap':side_av,'near_zone':near,'source':vw.get('source'),'basis_adjustment':vw.get('basis_adjustment',0)}}
            diagnostics['ranked'] += 1
            # Dynamic classification, not a lower-quality automatic signal: legitimate near-qualified
            # structures remain visible as WATCH candidates while the same 66 structural floor remains
            # the normal qualification reference. Break/retest and transition routes can qualify from
            # independent closed-candle evidence plus ranking, without requiring continuation state.
            precision_rescue=(pullback_bonus>0 and pullback_quality.get('score',0)>=58 and rank_score>=min_score and structural_score>=min_score-5)
            route_rescue=(route in ('BREAK_RETEST','TRANSITION') and rank_score>=min_score and structural_score>=min_score-5)
            qualifies = structural_score >= min_score or precision_rescue or route_rescue or (available and rank_score >= min_score and structural_score >= min_score-10)
            item['qualification_gap']=max(0,min_score-structural_score)
            item['qualification_threshold']=min_score
            item['candidate_competition_score']=rank_score
            if qualifies:
                item['status']='QUALIFIED_PRECISION_POINT'; diagnostics['qualified'] += 1
            elif structural_score>=max(52,min_score-14):
                item['status']='WATCH_CANDIDATE'; diagnostics['watch'] += 1
            else:
                diagnostics['rejected']['LOW_STRUCTURE']=diagnostics['rejected'].get('LOW_STRUCTURE',0)+1
            ranked_pool.append(dict(item))
            if not qualifies:
                continue
            item['note']=f'V39.3 M1 sequence-aware pullback-bridge qualified fresh M1 {mode.lower()} precision point. M5/M15/H1 are non-blocking context/confluence only. Quant evidence is not a probability or guarantee.'
            rows.append(item)

    rows.sort(key=lambda x:(x['score'],-x['distance_m1_atr']),reverse=True)
    ranked_pool.sort(key=lambda x:(x['ranking_score'],x['structural_score'],-x['distance_m1_atr']),reverse=True)
    if rows:
        dirs=sorted(set(x['side'] for x in rows))
        direction=(dirs[0] if len(dirs)==1 else 'BOTH')
        state='QUALIFIED_PRECISION_POINTS'
    else:
        direction='SEARCHING_BOTH' if context_direction=='MIXED' else context_direction+'_CONTEXT'
        state='NO_FRESH_QUALIFIED_M1_POINT'
    return {'state':state,'direction':direction,'context_direction':context_direction,'gate_score':max(bull_context,bear_context),'bull_gate':bull_context,'bear_gate':bear_context,'candidates':rows[:4],'ranked_candidate_pool':ranked_pool[:8],'m1_pullback':pullback_state,'pullback_quality':pullback_quality,'precision_engine_version':'V39.5_M1_CANDIDATE_LADDER_DIAGNOSTICS','candidate_diagnostics':diagnostics,'extra_route_candidates':extra_routes,'pullback_bridge_candidates':pullback_bridge,'compression_expansion':compression_expansion,'market_regime_v2':market_regime_v2,'tpo_profile':tpo,'initial_balance':initial_balance,'m5_structure':m5.get('structure'),'m5_momentum':m5.get('momentum'),'m5_pressure':m5.get('current_pressure'),'m15_structure':m15.get('structure'),'h1_structure':h1.get('structure'),'m1_structure':m1st,'m1_momentum':m1mom,'shock_caution':shock,'note':'V39.5 M1 CANDIDATE LADDER + DIAGNOSTICS: continuation pullback, break/retest and transition routes feed one ranked M1 candidate ladder. WATCH candidates expose near-qualified structure without pretending it is qualified. State integrity, memory and Regime 2.0 remain active.  M1 owns setup detection, candidate generation, qualification and precision ranking. GOOD/STRONG active pullbacks trigger a structural re-scan for fresh M1 FVG, displacement-origin and broken-structure retest candidates. M5/M15/H1 retain their structure, FVG/OB, liquidity and other concept analysis as non-blocking context/confluence only. Mathematical clustering, pullback geometry, micro-zone refinement, liquidity path/obstacles, redundancy control, freshness and Quant tracking remain active.'}

def build_reaction_engine(m5):
    """V32 deterministic closed-M5 reaction state for zones currently being tracked.
    Rejection alone is not confirmation; follow-through/structure evidence is required.
    """
    candles=m5.get('latest_closed_candles') or []
    atr=float(m5.get('atr14') or 1)
    cp=float(m5.get('data_current_price') or 0)
    allz=m5.get('all_candidate_zones') or m5.get('candidate_zones') or {}
    rows=[]
    for side in ('buy','sell'):
        for z in (allz.get(side) or [])[:8]:
            lo=float(z.get('low')); hi=float(z.get('high'))
            touched=[x for x in candles if x.get('l',1e99)<=hi and x.get('h',-1e99)>=lo]
            if not touched:
                state='WAIT'; ev=['zone not tested by recent closed M5 candles']
            else:
                last=candles[-1] if candles else {}; body=abs(float(last.get('c',0))-float(last.get('o',0))); rng=max(1e-9,float(last.get('h',0))-float(last.get('l',0)))
                if side=='buy':
                    invalid=sum(1 for x in candles[-2:] if float(x.get('c',0))<lo)>=2
                    reclaim=float(last.get('c',0))>=lo
                    wick=(float(last.get('c',0))-float(last.get('l',0)))>max(body*1.2,atr*.12)
                    follow=len(candles)>=2 and candles[-1]['c']>candles[-2]['c'] and candles[-1]['c']>candles[-1]['o']
                    struct=m5.get('structure_event') in ('BULLISH_CHOCH','BULLISH_BOS') or m5.get('structure')=='HH_HL'
                else:
                    invalid=sum(1 for x in candles[-2:] if float(x.get('c',0))>hi)>=2
                    reclaim=float(last.get('c',0))<=hi
                    wick=(float(last.get('h',0))-float(last.get('c',0)))>max(body*1.2,atr*.12)
                    follow=len(candles)>=2 and candles[-1]['c']<candles[-2]['c'] and candles[-1]['c']<candles[-1]['o']
                    struct=m5.get('structure_event') in ('BEARISH_CHOCH','BEARISH_BOS') or m5.get('structure')=='LL_LH'
                if invalid: state='INVALIDATED'; ev=['repeated closed-candle acceptance beyond zone']
                elif reclaim and wick and follow and struct: state='STRUCTURE_CONFIRMED'; ev=['rejection/reclaim','follow-through','structure confirmation']
                elif reclaim and follow: state='FOLLOW_THROUGH'; ev=['zone reclaimed/held','directional follow-through']
                elif reclaim and wick: state='REJECTION_RECLAIM'; ev=['wick rejection','closed-candle reclaim']
                else: state='TESTING'; ev=['recent closed candles interacting with zone']
            rows.append({'side':side.upper(),'low':round(lo,2),'high':round(hi,2),'source':z.get('source'),'state':state,'evidence':ev,'distance_atr':round((lo-cp)/atr,2) if side=='sell' else round((cp-hi)/atr,2)})
    priority={'STRUCTURE_CONFIRMED':6,'FOLLOW_THROUGH':5,'REJECTION_RECLAIM':4,'TESTING':3,'INVALIDATED':2,'WAIT':1}
    rows.sort(key=lambda x:priority.get(x['state'],0),reverse=True)
    return {'state':rows[0]['state'] if rows else 'NO_TRACKED_ZONE','active':rows[:6],'note':'Closed-M5 reaction states. A wick/rejection alone is not a confirmed setup.'}

def filter_fresh_candidates(mtf):
    """V30.1 presentation filter: only genuinely ahead-of-price, not-yet-used zones are new candidates.
    Historical/used zones remain in the underlying metrics for structure/context, but are not surfaced as new opportunities.
    """
    m5=(mtf.get('M5') or {}).get('metrics') or {}
    cz=m5.get('candidate_zones') or {}
    hidden={'buy':[],'sell':[]}; fresh={'buy':[],'sell':[]}
    for side in ('buy','sell'):
        for z in (cz.get(side) or []):
            stage=str(z.get('confirmation_stage') or 'WAIT').upper()
            touches=int(z.get('touch_count') or 0)
            consumption=str(z.get('consumption') or '').upper()
            # One interaction is allowed for the candle/structure that created an OB/FVG/origin.
            # Any recent test/rejection/follow-through or repeated interaction makes it USED for display.
            is_fresh=(stage=='WAIT' and touches<=1 and consumption in ('','UNTOUCHED','LIGHT'))
            z['display_fresh']=bool(is_fresh)
            z['freshness']='FRESH' if is_fresh else 'USED'
            if is_fresh: fresh[side].append(z)
            else:
                q=dict(z); q['hidden_reason']='Previously interacted with / reacted / consumed; retained internally as market evidence.'
                hidden[side].append(q)
    m5['all_candidate_zones']=cz
    fresh['buy']=fresh['buy'][:6]; fresh['sell']=fresh['sell'][:6]
    m5['candidate_zones']=fresh
    m5['hidden_used_zones']=hidden
    m5['opportunity_map']={'current_price':(m5.get('opportunity_map') or {}).get('current_price',m5.get('data_current_price')),'market_phase':m5.get('market_phase','UNCLEAR'),'buy_watch_areas':fresh['buy'],'sell_watch_areas':fresh['sell'],'purpose':'V34.2 fresh-only ahead-of-price candidates. A wider structural pool is filtered for freshness before display, so used high-ranked zones cannot crowd out valid fresh points.'}
    return mtf

def data_only_result(mtf,data_status,data_note,why='Gemini visual check unavailable'):
    m1=mtf.get('M1',{}).get('metrics',{}); m5=mtf.get('M5',{}).get('metrics',{}); m15=mtf.get('M15',{}).get('metrics',{}); h1=mtf.get('H1',{}).get('metrics',{})
    def top(side):
        arr=(m5.get('candidate_zones') or {}).get(side,[])
        return arr[0] if arr else None
    return {
      'mode':'DATA_ONLY','data_status':data_status,'data_note':data_note,'gemini_status':why,
      'current_price':(mtf.get('_price_meta') or {}).get('reference_price') if (mtf.get('_price_meta') or {}).get('reference_price') is not None else m5.get('data_current_price'),'price_source':'TWELVE_DATA_REFERENCE' if (mtf.get('_price_meta') or {}).get('reference_price') is not None else 'LATEST_M5_FEED_CANDLE','latest_m5_feed_close':m5.get('data_current_price'),'price_meta':mtf.get('_price_meta',{}),'current_pressure':m5.get('current_pressure','UNCLEAR'),
      'market_phase':m5.get('market_phase','UNCLEAR'),'shock_detector':m5.get('shock_detector','NORMAL'),
      'approach_speed':m5.get('approach_speed','UNCLEAR'),'m5_state':'BULLISH' if str(m5.get('momentum','')).startswith('BULLISH') else 'BEARISH' if str(m5.get('momentum','')).startswith('BEARISH') else 'UNCLEAR',
      'structure':m5.get('structure','UNCLEAR'),'structure_event':m5.get('structure_event','NONE'),'volatility':m5.get('volatility','NORMAL'),'momentum':m5.get('momentum','UNCLEAR'),
      'multi_timeframe_metrics':{'H1':h1,'M15':m15,'M5':m5,'M1':m1},'candidate_zones':m5.get('candidate_zones',{}),'opportunity_map':m5.get('opportunity_map',{}),
      'dynamic_pullback':m5.get('dynamic_pullback',{}),'transition_engine':m5.get('transition_engine',{}),'reaction_engine':m5.get('reaction_engine',{}),'m1_precision':m5.get('m1_precision',{}),'data_only_summary':f"H1 {h1.get('structure','—')} · M15 {m15.get('structure','—')} · M5 {m5.get('structure','—')}. V26 maps ahead-of-price pullback and new-move-origin candidates with H1/M15 confluence; Gemini visual confirmation unavailable.",
      'buy_candidate':top('buy'),'sell_candidate':top('sell'),
      'note':'Data-only analysis aid. Ahead-of-price watch areas are deterministic evidence locations, not predictions or guaranteed reversal points.'
    }


@app.route('/api/live-scan', methods=['GET','POST'])
def live_scan():
    """Screenshot-free live XAU/USD scan. Twelve Data + deterministic Python only; zero Gemini calls."""
    try:
        mtf,data_status,data_note=fetch_multitimeframe()
        if data_status not in ('LIVE_DATA','PARTIAL_DATA'):
            return jsonify({'error':'market_data_unavailable','detail':data_note}),503
        market_context=build_market_context(mtf)
        apply_market_context(mtf,market_context)
        filter_fresh_candidates(mtf)
        mtf['M5']['metrics']['reaction_engine']=build_reaction_engine(mtf['M5']['metrics'])
        mtf['M5']['metrics']['m1_precision']=build_m1_precision_engine(mtf, market_context.get('vwap_context',{}))
        apply_microstructure_context(mtf,market_context.get('vwap_context',{}),market_context.get('orderflow_context',{}))
        # V31: keep pullback state/candidate discovery separate from final display qualification.
        # This prevents a detected setup from silently disappearing between scans.
        m5=(mtf.get('M5') or {}).get('metrics') or {}
        dp=m5.get('dynamic_pullback') or {}
        dz=dp.get('candidate_zone') or {}
        if dz:
            side='buy' if str(dz.get('side')).upper()=='BUY' else 'sell'
            shown=False
            for z in ((m5.get('candidate_zones') or {}).get(side) or []):
                if z.get('source')==dz.get('source') and not (float(z.get('high',0)) < float(dz.get('low',0)) or float(z.get('low',0)) > float(dz.get('high',0))):
                    shown=True; break
            dp['final_display_qualified']=shown
            dp['candidate_status']='QUALIFIED_AND_DISPLAYED' if shown else 'DETECTED_NOT_FINAL_DISPLAY_QUALIFIED'
            if not shown:
                dp['note']=('Pullback state is active and a dynamic '+str(dz.get('side','')).upper()+
                            ' candidate was detected, but it did not pass the final fresh-zone display filter. It is tracked for this scan, not shown as a new point.')
        else:
            dp['final_display_qualified']=False
            dp['candidate_status']='NO_DYNAMIC_CANDIDATE'
        m5['dynamic_pullback']=dp
        out=data_only_result(mtf,data_status,data_note,'NOT_USED_LIVE_DATA_MODE')
        out['mode']='LIVE_DATA_CONTEXT'
        out['gemini_status']='NOT_USED'
        out['scanner_version']='V39.4 M1 PRECISION QUANT ENGINE'
        out['market_context']=market_context
        out['event_risk']=market_context.get('event_risk','UNKNOWN')
        out['data_only_summary']=out['data_only_summary'].replace('V26 maps','V30 maps')
        out['note']='V39 combines the forward-only Quant Engine with mathematical level clustering, pullback geometry, micro-zone refinement, liquidity path/obstacle analysis and evidence redundancy control. Statistics never create or move a zone. VWAP/AVWAP remain optional external context when unavailable server-side.'
        return jsonify(out)
    except Exception as e:
        return jsonify({'error':'live_scan_failed','detail':str(e)[:1200]}),500

@app.post('/api/scan')
def scan():
    try:
        d=request.get_json(force=True)
        if not d.get('m5'):return jsonify({'error':'missing_image','detail':'One fresh M5 screenshot is required for hybrid mode.'}),400
        event_risk='HIGH' if d.get('event_risk') else 'NORMAL'
        mtf,data_status,data_note=fetch_multitimeframe(); metrics=mtf.get('M5',{}).get('metrics',{})
        mtf_metrics={tf:v.get('metrics',{}) for tf,v in mtf.items()}
        price_meta=mtf.get('_price_meta',{}); context={'data_status':data_status,'data_note':data_note,'reference_price':price_meta.get('reference_price'),'price_meta':price_meta,'deterministic_metrics':metrics,'multi_timeframe_metrics':mtf_metrics,'event_risk':event_risk,'risk_budget':d.get('risk_budget'),'spread_cost':d.get('spread_cost'),'broker_specs':d.get('broker_specs'),'setup_memory':d.get('setup_memory'),'automatic_event_status':'UNKNOWN_NO_CALENDAR_FEED','input_guidance':'H1/M15/M5 are fetched automatically from OHLC. The user supplies only one fresh M5 screenshot. Evaluate BUY and SELL cases independently; H1/M15 are context, M5 is execution.'}
        try:
            result=run_model([PROMPT,'SERVER CONTEXT JSON:\n'+json.dumps(context,separators=(',',':')),image_part(d['m5'])])
            m5_live=(mtf.get('M5',{}).get('status')=='LIVE_DATA' and bool(mtf.get('M5',{}).get('candles'))); out=norm(result,metrics,data_status,event_risk,m5_live=m5_live); out['multi_timeframe_metrics']=mtf_metrics; out['mode']='HYBRID_OHLC_VISUAL'; out['gemini_status']='AVAILABLE'; out['m5_ohlc_live']=m5_live; out['timeframe_data_status']={tf:v.get('status') for tf,v in mtf.items() if not tf.startswith('_')}; out['price_meta']=price_meta; vp=out.get('screenshot_price'); rp=price_meta.get('reference_price'); atr=float(metrics.get('atr14') or 1);
            if vp is not None and rp is not None and abs(float(vp)-float(rp))>max(1.0,0.5*atr): out['data_ai_conflict']='MINOR' if abs(float(vp)-float(rp))<=max(3.0,1.5*atr) else 'MAJOR'; out['data_ai_conflict_reason']=f'MT5 screenshot price {vp:.3f} differs from Twelve Data reference {rp:.3f} by {abs(float(vp)-float(rp)):.3f}.'
            return jsonify(out)
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
    """Forward-test zone behavior including MFE/MAE. No profitability claim."""
    out={'time':setup.get('time'),'price':setup.get('price'),'market_phase':setup.get('market_phase'),'volatility_regime':setup.get('volatility_regime'),'session':setup.get('session'),'buy':'NO_ZONE','sell':'NO_ZONE'}
    if not candles:return out
    for side in ('buy','sell'):
        z=setup.get(side) or {}; bounds=parse_zone(z.get('zone')) if isinstance(z,dict) else None
        if not bounds:continue
        out[side+'_setup_type']=z.get('setup_type'); out[side+'_score']=z.get('score')
        lo,hi=bounds; touch_i=next((i for i,x in enumerate(candles) if x['l']<=hi and x['h']>=lo),None)
        if touch_i is None:out[side]='NOT_TRIGGERED';continue
        post=candles[touch_i:]; mid=(lo+hi)/2
        if side=='buy':
            invalid=any(x['c']<lo for x in post); mfe=max(x['h']-mid for x in post); mae=max(mid-x['l'] for x in post)
        else:
            invalid=any(x['c']>hi for x in post); mfe=max(mid-x['l'] for x in post); mae=max(x['h']-mid for x in post)
        # FOLLOW_THROUGH requires favorable movement after the first touch, not merely a wick/reaction.
        follow=False
        if len(post)>=2:
            if side=='buy':
                follow=any(post[i]['c']>hi and post[i]['c']>post[i-1]['c'] for i in range(1,len(post)))
            else:
                follow=any(post[i]['c']<lo and post[i]['c']<post[i-1]['c'] for i in range(1,len(post)))
        out[side]='INVALIDATED' if invalid else 'FOLLOW_THROUGH' if follow else 'REACTED' if mfe>0 else 'TESTED'
        out[side+'_mfe']=round(max(0,mfe),3); out[side+'_mae']=round(max(0,mae),3)
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
        
        groups={}
        for r in results:
            for side in ('buy','sell'):
                typ=r.get(side+'_setup_type')
                if not typ:continue
                g=groups.setdefault(typ,{'samples':0,'triggered':0,'reacted':0,'invalidated':0,'mfe':[],'mae':[]})
                g['samples']+=1; state=r.get(side)
                if state!='NOT_TRIGGERED':g['triggered']+=1
                if state in ('REACTED','FOLLOW_THROUGH'):g['reacted']+=1
                if state=='INVALIDATED':g['invalidated']+=1
                if r.get(side+'_mfe') is not None:g['mfe'].append(r[side+'_mfe'])
                if r.get(side+'_mae') is not None:g['mae'].append(r[side+'_mae'])
        summary={}
        for k,g in groups.items():
            summary[k]={'samples':g['samples'],'triggered':g['triggered'],'reacted':g['reacted'],'invalidated':g['invalidated'],'reaction_rate_of_triggered':round(100*g['reacted']/g['triggered'],1) if g['triggered'] else None,'avg_mfe':round(sum(g['mfe'])/len(g['mfe']),3) if g['mfe'] else None,'avg_mae':round(sum(g['mae'])/len(g['mae']),3) if g['mae'] else None}
        return jsonify({'status':'LIVE_DATA','note':'Forward statistics measure zone behavior only; sample size matters and this is not a guaranteed win rate.','counts':counts,'by_setup_type':summary,'outcomes':results})
    except Exception as e:return jsonify({'error':'outcome_failed','detail':str(e)[:800]}),500


def evaluate_precision_setup(setup, candles):
    """Forward-only M1 grading for a frozen precision point. Uses only candles at/after first_seen.
    Meaningful reaction = >= 1.0 setup-time ATR favorable excursion before a closed-candle invalidation.
    This measures zone behavior, not trade P&L or win probability.
    """
    side=str(setup.get('side') or '').upper()
    try:
        lo=float(setup.get('low')); hi=float(setup.get('high')); atr=float(setup.get('atr14') or 0)
    except Exception:
        return None
    if side not in ('BUY','SELL') or hi < lo or atr <= 0 or not candles:return None
    touch_i=next((i for i,x in enumerate(candles) if float(x['l'])<=hi and float(x['h'])>=lo),None)
    base={'id':setup.get('id'),'side':side,'source':setup.get('source'),'depth':setup.get('depth'),'point_class':setup.get('point_class'),'mode':setup.get('mode'),'context_direction':setup.get('context_direction'),'session':setup.get('session'),'pullback_grade':setup.get('pullback_grade'),'pullback_score':setup.get('pullback_score'),'market_phase':setup.get('market_phase'),'volatility_regime':setup.get('volatility_regime'),'m1_structure':setup.get('m1'),'m1_momentum':setup.get('m1_momentum'),'regime_v2':setup.get('regime_v2'),'compression_state':setup.get('compression_state'),'atr14':round(atr,4)}
    if touch_i is None:
        return {**base,'state':'NOT_TRIGGERED','meaningful_reaction':False,'mfe_atr':None,'mae_atr':None}
    post=candles[touch_i:]
    mid=(lo+hi)/2.0; best=0.0; adverse=0.0; invalid_at=None
    for j,x in enumerate(post):
        h,l,c=float(x['h']),float(x['l']),float(x['c'])
        if side=='BUY':
            best=max(best,h-mid); adverse=max(adverse,mid-l); invalid=(c<lo)
        else:
            best=max(best,mid-l); adverse=max(adverse,h-mid); invalid=(c>hi)
        if invalid:
            invalid_at=j; break
    mfe=max(0.0,best)/atr; mae=max(0.0,adverse)/atr
    meaningful=mfe>=1.0
    state='MEANINGFUL_REACTION' if meaningful else ('INVALIDATED' if invalid_at is not None else 'TESTED')
    return {**base,'state':state,'meaningful_reaction':meaningful,'invalidated':invalid_at is not None,'mfe_atr':round(mfe,2),'mae_atr':round(mae,2),'bars_to_invalidation':invalid_at}

def quant_summary(rows):
    triggered=[r for r in rows if r and r.get('state')!='NOT_TRIGGERED']
    n=len(triggered); reacted=[r for r in triggered if r.get('meaningful_reaction')]
    invalid=[r for r in triggered if r.get('invalidated')]
    mf=[r['mfe_atr'] for r in triggered if isinstance(r.get('mfe_atr'),(int,float))]
    ma=[r['mae_atr'] for r in triggered if isinstance(r.get('mae_atr'),(int,float))]
    avg_mfe=round(sum(mf)/len(mf),2) if mf else None; avg_mae=round(sum(ma)/len(ma),2) if ma else None
    net=round(avg_mfe-avg_mae,2) if avg_mfe is not None and avg_mae is not None else None
    confidence='INSUFFICIENT' if n<20 else 'DEVELOPING' if n<50 else 'GOOD' if n<100 else 'STRONG_SAMPLE'
    return {'samples':n,'meaningful_reactions':len(reacted),'reaction_rate':round(100*len(reacted)/n,1) if n else None,'invalidated':len(invalid),'avg_mfe_atr':avg_mfe,'avg_mae_atr':avg_mae,'net_excursion_atr':net,'sample_confidence':confidence}

def quant_similarity(results, setups):
    """Nearest categorical setup cohort. Descriptive only; never changes a point."""
    if not results or not setups:return {'status':'INSUFFICIENT_SAMPLE','similar_samples':0}
    latest=setups[0]
    fields=('side','source','depth','mode','context_direction','pullback_grade','m1','m1_momentum','regime_v2','compression_state')
    scored=[]
    for r in results:
        if r.get('id')==latest.get('id'): continue
        matches=sum(1 for f in fields if latest.get(f) and r.get({'m1':'m1_structure'}.get(f,f))==latest.get(f))
        scored.append((matches,r))
    scored.sort(key=lambda x:x[0],reverse=True)
    cohort=[r for score,r in scored if score>=max(3,scored[0][0]-1)] if scored else []
    cohort=cohort[:60]
    q=quant_summary(cohort)
    q.update({'status':'INSUFFICIENT_SAMPLE' if q['samples']<20 else 'DEVELOPING' if q['samples']<50 else 'USABLE_CONTEXT','match_fields':list(fields),'latest_setup_id':latest.get('id')})
    return q

@app.post('/api/quant')
def quant_engine():
    """V38.1 forward-only Quant Engine for frozen M1 precision points supplied by the phone."""
    try:
        d=request.get_json(force=True); setups=(d.get('setups') or [])[:250]
        candles,st,note=fetch_tf('1min',500)
        if not candles:return jsonify({'status':st,'note':note,'summary':quant_summary([]),'groups':{}})
        results=[]
        for x in setups:
            t=str(x.get('first_seen') or '').replace('T',' ')[:16]
            after=[c for c in candles if str(c.get('t',''))[:16]>=t] if t else []
            r=evaluate_precision_setup(x,after)
            if r:results.append(r)
        groups={}
        for field in ('source','depth','mode','context_direction','session','pullback_grade'):
            vals={}
            for r in results:
                key=str(r.get(field) or 'UNKNOWN'); vals.setdefault(key,[]).append(r)
            groups[field]={k:quant_summary(v) for k,v in vals.items()}
        return jsonify({'status':'LIVE_DATA','quant_version':'V39.4','definition':'Meaningful reaction = at least 1.0 setup-time M1 ATR favorable excursion after first touch and before closed-candle invalidation.','summary':quant_summary(results),'groups':groups,'similarity':quant_similarity(results,setups),'results':results,'note':'Forward-only zone-behavior statistics from frozen precision points. Reaction rate is not a win rate; net excursion is avg MFE minus avg MAE, not trading P&L.'})
    except Exception as e:return jsonify({'error':'quant_failed','detail':str(e)[:900]}),500

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
