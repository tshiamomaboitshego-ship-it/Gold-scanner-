from flask import Flask, jsonify, render_template, request
from datetime import datetime, timedelta, timezone, date
import math, threading, time

app = Flask(__name__, template_folder=".")
UTC = timezone.utc
DATA_LOCK = threading.Lock()
GOLD_CACHE = {"at": 0, "frame": None, "error": None}

try:
    import swisseph as swe
    SWE_OK = True
    swe.set_ephe_path('.')
except Exception:
    SWE_OK = False
    swe = None

PLANETS = {
    "Sun": getattr(swe, 'SUN', 0) if SWE_OK else 0,
    "Moon": getattr(swe, 'MOON', 1) if SWE_OK else 1,
    "Mercury": getattr(swe, 'MERCURY', 2) if SWE_OK else 2,
    "Venus": getattr(swe, 'VENUS', 3) if SWE_OK else 3,
    "Mars": getattr(swe, 'MARS', 4) if SWE_OK else 4,
    "Jupiter": getattr(swe, 'JUPITER', 5) if SWE_OK else 5,
    "Saturn": getattr(swe, 'SATURN', 6) if SWE_OK else 6,
    "Uranus": getattr(swe, 'URANUS', 7) if SWE_OK else 7,
    "Neptune": getattr(swe, 'NEPTUNE', 8) if SWE_OK else 8,
    "Pluto": getattr(swe, 'PLUTO', 9) if SWE_OK else 9,
}
SIGNS = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces']
ASPECTS = [(0,'Conjunction'),(60,'Sextile'),(90,'Square'),(120,'Trine'),(180,'Opposition')]


def jd_for(dt):
    dt = dt.astimezone(UTC)
    hour = dt.hour + dt.minute/60 + dt.second/3600 + dt.microsecond/3.6e9
    return swe.julday(dt.year, dt.month, dt.day, hour, swe.GREG_CAL)


def planet_longitudes(dt):
    if not SWE_OK:
        raise RuntimeError('Astronomy engine is unavailable. Check the deployed pyswisseph dependency.')
    jd = jd_for(dt)
    result = {}
    for name, body in PLANETS.items():
        xx, _ = swe.calc_ut(jd, body, swe.FLG_MOSEPH | swe.FLG_SPEED)
        result[name] = {"longitude": float(xx[0] % 360), "speed": float(xx[3]), "sign": SIGNS[int((xx[0] % 360)//30)], "degree": float(xx[0] % 30)}
    return result


def phase_angle(dt):
    if not SWE_OK: raise RuntimeError('Astronomy engine is unavailable.')
    jd = jd_for(dt)
    moon, _ = swe.calc_ut(jd, swe.MOON, swe.FLG_MOSEPH)
    sun, _ = swe.calc_ut(jd, swe.SUN, swe.FLG_MOSEPH)
    return (moon[0] - sun[0]) % 360


def norm_delta(x):
    return (x + 180) % 360 - 180


def find_phase_events(start, end):
    # Scan phase angle and refine crossings of 0/90/180/270 degrees.
    if not SWE_OK: return []
    events = []
    step = timedelta(hours=6)
    t0 = start.astimezone(UTC)
    a0 = phase_angle(t0)
    t = t0 + step
    targets = {0: 'New Moon', 90: 'First Quarter', 180: 'Full Moon', 270: 'Last Quarter'}
    while t <= end.astimezone(UTC):
        a1 = phase_angle(t)
        advance = (a1 - a0) % 360
        if advance > 180:  # defensive: no expected reverse leap over a six-hour interval
            advance = 360 - advance
        for target, label in targets.items():
            distance = (target - a0) % 360
            if distance < 1e-7: distance = 360
            if 0 < distance <= advance + 1e-8:
                left, right = t - step, t
                base_angle = phase_angle(left)
                target_distance = (target - base_angle) % 360
                for _ in range(24):
                    mid = left + (right-left)/2
                    mid_distance = (phase_angle(mid) - base_angle) % 360
                    if mid_distance < target_distance:
                        left = mid
                    else:
                        right = mid
                moment = left + (right-left)/2
                if start.astimezone(UTC) <= moment <= end.astimezone(UTC):
                    events.append({"date": moment.isoformat(), "name": label, "angle": target})
        a0 = a1
        t += step
    dedup = {}
    for e in events: dedup[(e['name'], e['date'][:16])] = e
    return sorted(dedup.values(), key=lambda x:x['date'])


def get_gold_frame():
    now = time.time()
    with DATA_LOCK:
        if GOLD_CACHE['frame'] is not None and now - GOLD_CACHE['at'] < 1800:
            return GOLD_CACHE['frame'], GOLD_CACHE['error']
        try:
            import yfinance as yf
            df = yf.download('XAUUSD=X', period='10y', interval='1d', auto_adjust=False, progress=False, threads=False)
            if df is None or df.empty:
                raise RuntimeError('Yahoo Finance returned no XAUUSD daily history.')
            if hasattr(df.columns, 'levels') and len(df.columns.levels) > 1:
                close = df['Close'].iloc[:,0] if getattr(df['Close'], 'ndim', 1) > 1 else df['Close']
            else:
                close = df['Close']
            close = close.dropna()
            frame = close.to_frame(name='Close')
            frame.index = frame.index.tz_localize(None) if getattr(frame.index, 'tz', None) is not None else frame.index
            GOLD_CACHE.update(at=now, frame=frame, error=None)
            return frame, None
        except Exception as exc:
            GOLD_CACHE.update(at=now, frame=None, error=str(exc))
            return None, str(exc)


def moon_phase_name(angle):
    a = angle % 360
    if a < 22.5 or a >= 337.5: return 'New Moon'
    if a < 67.5: return 'Waxing Crescent'
    if a < 112.5: return 'First Quarter'
    if a < 157.5: return 'Waxing Gibbous'
    if a < 202.5: return 'Full Moon'
    if a < 247.5: return 'Waning Gibbous'
    if a < 292.5: return 'Last Quarter'
    return 'Waning Crescent'


def current_aspects(dt, orb=3.0):
    positions = planet_longitudes(dt)
    names = list(positions.keys())
    rows=[]
    for i, a in enumerate(names):
        for b in names[i+1:]:
            delta = abs(norm_delta(positions[a]['longitude'] - positions[b]['longitude']))
            aspect, label = min(ASPECTS, key=lambda x: abs(delta-x[0]))
            diff = abs(delta-aspect)
            if diff <= orb:
                rows.append({"planet1":a,"planet2":b,"aspect":label,"angle":aspect,"orb":round(diff,2),"exactness":"applying/ separating not inferred"})
    return sorted(rows, key=lambda r:r['orb']), positions


def gold_phase_stats():
    frame, error = get_gold_frame()
    if frame is None:
        return {"available":False,"error":error,"source":"Yahoo Finance XAUUSD=X daily data"}
    import pandas as pd
    close = frame['Close'].dropna()
    close.index = pd.to_datetime(close.index).tz_localize(None)
    phase_events = find_phase_events(datetime.now(UTC)-timedelta(days=3650), datetime.now(UTC))
    stats=[]
    for phase in ['New Moon','First Quarter','Full Moon','Last Quarter']:
        returns = {1:[],3:[],5:[]}
        vol=[]
        used=0
        for ev in phase_events:
            if ev['name'] != phase: continue
            idx = close.index.searchsorted(pd.Timestamp(ev['date']).tz_localize(None), side='left')
            if idx >= len(close)-6: continue
            base=float(close.iloc[idx])
            if base == 0: continue
            used += 1
            for n in returns:
                val=float(close.iloc[idx+n])
                returns[n].append((val/base-1)*100)
            daily=close.pct_change().iloc[idx:idx+5].dropna()*100
            if len(daily): vol.append(float(daily.std()))
        windows={}
        for n, vals in returns.items():
            windows[str(n)]={"n":len(vals),"avg_pct":round(sum(vals)/len(vals),3) if vals else None,"positive_pct":round(sum(v>0 for v in vals)/len(vals)*100,1) if vals else None,"median_pct":round(float(pd.Series(vals).median()),3) if vals else None}
        stats.append({"phase":phase,"events_used":used,"returns":windows,"avg_5day_daily_volatility_pct":round(sum(vol)/len(vol),3) if vol else None})
    return {"available":True,"source":"Yahoo Finance XAUUSD=X daily closes; approximate event-to-next-trading-session alignment","stats":stats,"observations":len(close),"from":str(close.index.min().date()),"to":str(close.index.max().date()),"caveat":"Exploratory, unadjusted historical associations; not a causal effect or validated trading edge. Weekend/holiday phase events are matched to the next available daily close."}


@app.get('/')
def home():
    return render_template('index.html')

@app.get('/health')
def health():
    return jsonify({"ok":True,"ephemeris_available":SWE_OK,"app":"Gold Lunar & Astrology Research Lab"})

@app.get('/api/overview')
def overview():
    now=datetime.now(UTC)
    try:
        angle=phase_angle(now)
        phase=moon_phase_name(angle)
        aspects, positions=current_aspects(now)
        phases=find_phase_events(now-timedelta(days=1), now+timedelta(days=60))
        next_phase=next((x for x in phases if datetime.fromisoformat(x['date'])>now), None)
        planet_list=[{"name":k,"sign":v['sign'],"degree":round(v['degree'],2),"longitude":round(v['longitude'],2),"retrograde":v['speed']<0} for k,v in positions.items()]
        return jsonify({"as_of":now.isoformat(),"phase":phase,"illumination_pct":round((1-math.cos(math.radians(angle)))/2*100,1),"phase_angle":round(angle,1),"next_phase":next_phase,"phases":phases,"planets":planet_list,"aspects":aspects,"engine":"Swiss Ephemeris Moshier analytical ephemeris","timezone":"UTC; display converted to Africa/Johannesburg in browser"})
    except Exception as exc:
        return jsonify({"error":str(exc),"ephemeris_available":SWE_OK}),503

@app.get('/api/gold-stats')
def gold_stats():
    return jsonify(gold_phase_stats())

@app.get('/api/history')
def history():
    frame, error = get_gold_frame()
    if frame is None: return jsonify({"available":False,"error":error,"source":"Yahoo Finance XAUUSD=X"}),503
    tail=frame.tail(260)
    out=[]
    for idx,row in tail.iterrows():
        val=float(row['Close'])
        if math.isfinite(val): out.append({"date":idx.strftime('%Y-%m-%d'),"close":round(val,2)})
    return jsonify({"available":True,"source":"Yahoo Finance XAUUSD=X daily close; third-party data can be delayed or unavailable","data":out})

@app.get('/api/events')
def events():
    try:
        now=datetime.now(UTC)
        days=max(1,min(180,int(request.args.get('days',60))))
        start=now-timedelta(days=min(90,int(request.args.get('past',30))))
        end=now+timedelta(days=days)
        phases=find_phase_events(start,end)
        return jsonify({"events":phases,"start":start.isoformat(),"end":end.isoformat()})
    except Exception as exc: return jsonify({"error":str(exc)}),503

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=False)
