import os
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
import swisseph as swe

app = FastAPI(title="Vedic Cosmic Chakra API")

# Enable CORS for all incoming browser requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set Lahiri Ayanamsa
swe.set_sid_mode(swe.SIDM_LAHIRI)

PLANET_IDS = {
    "sun": swe.SUN,
    "moon": swe.MOON,
    "mars": swe.MARS,
    "mercury": swe.MERCURY,
    "jupiter": swe.JUPITER,
    "venus": swe.VENUS,
    "saturn": swe.SATURN,
    "rahu": swe.MEAN_NODE,
}

def get_julian_day(utc_datetime: datetime) -> float:
    return swe.julday(
        utc_datetime.year,
        utc_datetime.month,
        utc_datetime.day,
        utc_datetime.hour + utc_datetime.minute / 60.0 + utc_datetime.second / 3600.0
    )

def calculate_positions(utc_dt: datetime):
    jd = get_julian_day(utc_dt)
    positions = {}
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
    
    for planet_name, planet_id in PLANET_IDS.items():
        res, _ = swe.calc_ut(jd, planet_id, flags)
        positions[planet_name] = res[0] % 360

    positions["ketu"] = (positions["rahu"] + 180) % 360
    return positions

@app.get("/", response_class=HTMLResponse)
def read_root():
    # Serves transit_wheel.html directly at root
    if os.path.exists("transit_wheel.html"):
        with open("transit_wheel.html", "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>transit_wheel.html not found in root directory!</h1>"

@app.get("/current-positions")
def current_positions():
    now_utc = datetime.now(timezone.utc)
    positions = calculate_positions(now_utc)
    return {
        "status": "success",
        "date_str": now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "positions": positions
    }

@app.get("/step-time")
def step_time(base_date: str, days_delta: float):
    try:
        clean_date_str = base_date.replace(" UTC", "")
        dt_utc = datetime.strptime(clean_date_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        new_dt = dt_utc + timedelta(days=days_delta)
        positions = calculate_positions(new_dt)
        return {
            "status": "success",
            "date_str": new_dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "positions": positions
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Dynamically bind to Render's assigned PORT
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
