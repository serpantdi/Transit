from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import swisseph as swe
import datetime
import os

app = FastAPI()

# Enable cross-origin resource sharing for smooth front-end interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PLANET_MAP = {
    "sun": swe.SUN, "moon": swe.MOON, "mars": swe.MARS,
    "mercury": swe.MERCURY, "jupiter": swe.JUPITER,
    "venus": swe.VENUS, "saturn": swe.SATURN,
    "rahu": swe.TRUE_NODE
}

@app.get("/", response_class=HTMLResponse)
def serve_homepage():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>index.html not found!</h1>"

def get_julian_date(dt: datetime.datetime):
    return swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute/60.0)

def get_planet_long(jd, planet_id):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    res = swe.calc_ut(jd, planet_id, swe.FLG_SIDEREAL)
    return res[0][0]

def get_all_positions_at_jd(jd):
    positions = {}
    for name, p_id in PLANET_MAP.items():
        positions[name] = round(get_planet_long(jd, p_id), 2)
    # Calculate shadow planet Ketu perfectly 180 degrees opposite of Rahu
    positions["ketu"] = round((positions["rahu"] + 180) % 360, 2)
    return positions

@app.get("/current-positions")
def current_positions():
    now = datetime.datetime.utcnow()
    jd_now = get_julian_date(now)
    return {
        "date_str": now.strftime("%Y-%m-%d %H:%M UTC"),
        "positions": get_all_positions_at_jd(jd_now)
    }

@app.get("/step-time")
def step_time(base_date: str, days_delta: float):
    try:
        dt = datetime.datetime.strptime(base_date, "%Y-%m-%d %H:%M UTC")
    except Exception:
        dt = datetime.datetime.utcnow()

    jd = get_julian_date(dt) + days_delta
    y, m, d, h = swe.revjul(jd)
    
    # Safely extract hour and minute components
    hour_int = int(h)
    minute = int((h - hour_int) * 60)
    if minute >= 60: minute = 59
    if minute < 0: minute = 0
    
    new_date_str = datetime.datetime(y, m, d, hour_int, minute).strftime("%Y-%m-%d %H:%M UTC")
    
    return {
        "date_str": new_date_str,
        "positions": get_all_positions_at_jd(jd)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
