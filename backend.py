import os
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
import swisseph as swe

app = FastAPI(title="Vedic Cosmic Chakra API")

# Enable CORS for Render deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Swiss Ephemeris configuration (Sidereal / Lahiri)
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
    
    # Calculate Sidereal planetary positions
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
    
    for planet_name, planet_id in PLANET_IDS.items():
        res, _ = swe.calc_ut(jd, planet_id, flags)
        positions[planet_name] = res[0] % 360

    # Ketu is exactly 180 degrees opposite Rahu
    positions["ketu"] = (positions["rahu"] + 180) % 360

    return positions

@app.get("/", response_class=HTMLResponse)
def read_root():
    if os.path.exists("transit_wheel.html"):
        with open("transit_wheel.html", "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Transit Wheel HTML file not found!</h1>"

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

@app.post("/calculate-birth-chart")
def calculate_birth_chart(
    name: str = Form(...),
    dob: str = Form(...),
    tob: str = Form(...),
    city: str = Form(...),
    tz_offset: float = Form(...)
):
    try:
        local_dt = datetime.strptime(f"{dob} {tob}", "%Y-%m-%d %H:%M")
        utc_dt = local_dt - timedelta(hours=tz_offset)
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
        
        positions = calculate_positions(utc_dt)
        jd = get_julian_day(utc_dt)
        
        # Calculate Ascendant (Lagna) - Defaulting to center coordinates if city lookup absent
        lat, lon = 16.5449, 81.5212  # Default coordinates
        cusps, ascmc = swe.houses_ex(jd, lat, lon, b'A', flags=swe.FLG_SIDEREAL)
        ascendant = ascmc[0] % 360

        return {
            "status": "success",
            "name": name,
            "dob": dob,
            "tob": tob,
            "ascendant": ascendant,
            "positions": positions
        }
    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend:app", host="0.0.0.0", port=10000, reload=True)
