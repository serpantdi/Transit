from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import swisseph as swe
import datetime
import requests
import os

app = FastAPI()

# Enable CORS for all incoming requests on Render
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
    "rahu": swe.MEAN_NODE  # Mean Node for consistent calculations
}

# --- Parashari Ashtakavarga Engine Data & Logic ---

AV_RULES = {
    "sun": {
        "sun": [1, 2, 4, 7, 8, 9, 10, 11],
        "moon": [3, 6, 10, 11],
        "mars": [1, 2, 4, 7, 8, 9, 10, 11],
        "mercury": [3, 5, 6, 9, 10, 11, 12],
        "jupiter": [5, 6, 9, 11],
        "venus": [6, 7, 12],
        "saturn": [1, 2, 4, 7, 8, 9, 10, 11],
        "lagna": [3, 4, 6, 10, 11, 12]
    },
    "moon": {
        "sun": [3, 6, 7, 8, 10, 11],
        "moon": [1, 3, 6, 7, 10, 11],
        "mars": [2, 3, 5, 6, 9, 10, 11],
        "mercury": [1, 3, 4, 5, 7, 8, 10, 11],
        "jupiter": [1, 4, 7, 8, 10, 11, 12],
        "venus": [3, 4, 5, 7, 9, 10, 11],
        "saturn": [3, 5, 6, 11],
        "lagna": [3, 6, 10, 11]
    },
    "mars": {
        "sun": [3, 5, 6, 10, 11],
        "moon": [3, 6, 11],
        "mars": [1, 2, 4, 7, 8, 9, 10, 11],
        "mercury": [3, 5, 6, 11],
        "jupiter": [6, 10, 11, 12],
        "venus": [6, 8, 11, 12],
        "saturn": [1, 4, 7, 8, 9, 10, 11],
        "lagna": [1, 3, 6, 10, 11]
    },
    "mercury": {
        "sun": [5, 6, 9, 11, 12],
        "moon": [2, 4, 6, 8, 10, 11],
        "mars": [1, 2, 4, 7, 8, 9, 10, 11],
        "mercury": [1, 3, 5, 6, 9, 10, 11, 12],
        "jupiter": [6, 8, 11, 12],
        "venus": [1, 2, 3, 4, 5, 8, 9, 11],
        "saturn": [1, 2, 4, 7, 8, 9, 10, 11],
        "lagna": [1, 2, 4, 6, 8, 10, 11]
    },
    "jupiter": {
        "sun": [1, 2, 3, 4, 7, 8, 9, 10, 11],
        "moon": [2, 5, 7, 9, 11],
        "mars": [1, 2, 4, 7, 8, 10, 11],
        "mercury": [1, 2, 4, 5, 6, 9, 10, 11],
        "jupiter": [1, 2, 3, 4, 7, 8, 10, 11],
        "venus": [2, 5, 6, 9, 10, 11],
        "saturn": [3, 5, 6, 12],
        "lagna": [1, 2, 4, 5, 6, 7, 9, 10, 11]
    },
    "venus": {
        "sun": [8, 11, 12],
        "moon": [1, 2, 3, 4, 5, 8, 9, 11, 12],
        "mars": [3, 5, 6, 9, 11, 12],
        "mercury": [3, 5, 6, 9, 11],
        "jupiter": [5, 8, 9, 10, 11],
        "venus": [1, 2, 3, 4, 5, 8, 9, 10, 11],
        "saturn": [3, 4, 5, 8, 9, 10, 11],
        "lagna": [1, 2, 3, 4, 5, 8, 9, 11]
    },
    "saturn": {
        "sun": [1, 2, 4, 7, 8, 10, 11],
        "moon": [3, 6, 11],
        "mars": [3, 5, 6, 10, 11, 12],
        "mercury": [6, 8, 9, 10, 11, 12],
        "jupiter": [5, 6, 11, 12],
        "venus": [6, 11, 12],
        "saturn": [3, 5, 6, 11],
        "lagna": [1, 3, 4, 6, 10, 11]
    }
}

def calculate_ashtakavarga(positions: dict, ascendant_long: float):
    """Calculates Bhinna Ashtakavarga (BAV) and Samudaya Ashtakavarga (SAV)."""
    sign_positions = {p: int(positions[p] // 30) for p in AV_RULES["sun"].keys() if p in positions}
    sign_positions["lagna"] = int(ascendant_long // 30)

    bav = {p: [0] * 12 for p in AV_RULES.keys()}
    sav = [0] * 12

    for target_planet, contributors in AV_RULES.items():
        for contributor, houses in contributors.items():
            if contributor in sign_positions:
                ref_sign = sign_positions[contributor]
                for h in houses:
                    sign_idx = (ref_sign + h - 1) % 12
                    bav[target_planet][sign_idx] += 1

    for planet_points in bav.values():
        for i in range(12):
            sav[i] += planet_points[i]

    return {"bav": bav, "sav": sav}

# --- HTML Page Routes ---

@app.get("/", response_class=HTMLResponse)
def serve_homepage():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>index.html not found!</h1>"

@app.get("/birth-chart", response_class=HTMLResponse)
def serve_birth_chart():
    if os.path.exists("birth_chart.html"):
        with open("birth_chart.html", "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>birth_chart.html not found!</h1>"

@app.get("/transit-wheel", response_class=HTMLResponse)
def serve_transit_wheel():
    if os.path.exists("transit_wheel.html"):
        with open("transit_wheel.html", "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>transit_wheel.html not found!</h1>"


# --- Astrological Calculations ---

def get_julian_date(dt: datetime.datetime):
    return swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute/60.0 + dt.second/3600.0)

def get_planet_long(jd, planet_id):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    res = swe.calc_ut(jd, planet_id, swe.FLG_SIDEREAL)
    return res[0][0]

def get_all_positions_at_jd(jd):
    positions = {}
    for name, p_id in PLANET_MAP.items():
        positions[name] = round(get_planet_long(jd, p_id), 2)
    positions["ketu"] = round((positions["rahu"] + 180) % 360, 2)
    return positions


# --- API Endpoints ---

@app.get("/current-positions")
def current_positions():
    now = datetime.datetime.now(datetime.timezone.utc)
    jd_now = get_julian_date(now)
    return {
        "date_str": now.strftime("%Y-%m-%d %H:%M UTC"),
        "positions": get_all_positions_at_jd(jd_now)
    }

@app.get("/step-time")
def step_time(base_date: str, days_delta: float):
    try:
        clean_date_str = base_date.replace(" UTC", "")
        dt = datetime.datetime.strptime(clean_date_str, "%Y-%m-%d %H:%M").replace(tzinfo=datetime.timezone.utc)
    except Exception:
        dt = datetime.datetime.now(datetime.timezone.utc)

    jd = get_julian_date(dt) + days_delta
    y, m, d, h = swe.revjul(jd)
    
    hour_int = int(h)
    minute = int((h - hour_int) * 60)
    if minute >= 60: minute = 59
    if minute < 0: minute = 0
    
    new_date_str = datetime.datetime(y, m, d, hour_int, minute).strftime("%Y-%m-%d %H:%M UTC")
    
    return {
        "date_str": new_date_str,
        "positions": get_all_positions_at_jd(jd)
    }

@app.post("/calculate-birth-chart")
def calculate_birth_chart(
    name: str = Form(...),
    dob: str = Form(...),          # YYYY-MM-DD
    tob: str = Form(...),          # HH:MM
    city: str = Form(...),         # City Name
    tz_offset: float = Form(5.5)   # Timezone offset in hours
):
    try:
        geo_url = f"https://nominatim.openstreetmap.org/search?q={city}&format=json&limit=1"
        headers = {"User-Agent": "AstroMatrixApp/1.0"}
        geo_res = requests.get(geo_url, headers=headers).json()
        
        if not geo_res:
            return {"status": "error", "message": f"City '{city}' not found. Please specify country name."}
        
        lat = float(geo_res[0]["lat"])
        lon = float(geo_res[0]["lon"])
        location_name = geo_res[0]["display_name"]

        dt_local = datetime.datetime.strptime(f"{dob} {tob}", "%Y-%m-%d %H:%M")
        dt_utc = dt_local - datetime.timedelta(hours=tz_offset)
        
        jd_utc = get_julian_date(dt_utc)
        
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        positions = get_all_positions_at_jd(jd_utc)
        
        cusps, ascmc = swe.houses_ex(jd_utc, lat, lon, b'E', swe.FLG_SIDEREAL)
        ascendant_long = round(ascmc[0], 2)
        
        # Calculate Ashtakavarga
        av_results = calculate_ashtakavarga(positions, ascendant_long)

        return {
            "status": "success",
            "name": name,
            "dob": dob,
            "tob": tob,
            "location": location_name,
            "ascendant": ascendant_long,
            "positions": positions,
            "sav": av_results["sav"],
            "bav": av_results["bav"]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    # Dynamically bind to Render's port environment variable
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
