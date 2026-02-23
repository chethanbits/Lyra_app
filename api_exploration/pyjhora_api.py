"""
PyJHora wrapped as a REST API using FastAPI.
==============================================

This is what Chethan asked for:
  "Check if you can wrap PyJHora into an API interface"
  "Pass date/time/location and it generates planetary position for 28 years from DOB"

HOW TO RUN:
  cd api_exploration
  .\\venv\\Scripts\\activate
  uvicorn pyjhora_api:app --reload --port 8000

THEN OPEN IN BROWSER:
  http://localhost:8000/docs     <- Interactive API docs (try it out!)
  http://localhost:8000/         <- Welcome page
"""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="PyJHora Astrology API",
    description="Vedic Astrology API powered by PyJHora (free, runs locally)",
    version="1.0.1",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import PyJHora
from jhora.panchanga import drik
from jhora import utils

# Geocoding (city name -> lat/lon/timezone)
from geopy.geocoders import ArcGIS
from timezonefinder import TimezoneFinder
import pytz
from datetime import datetime as dt

_geocoder = ArcGIS()
_tz_finder = TimezoneFinder()

from datetime import timedelta

SIGNS = [
    "Mesha/Aries", "Vrishabha/Taurus", "Mithuna/Gemini", "Kataka/Cancer",
    "Simha/Leo", "Kanya/Virgo", "Tula/Libra", "Vrischika/Scorpio",
    "Dhanus/Sagittarius", "Makara/Capricorn", "Kumbha/Aquarius", "Meena/Pisces",
]

# Swiss Ephemeris order (THIS IS THE CORRECT ORDER!)
PLANET_INDICES = {
    "Sun": 0,
    "Moon": 1,
    "Mercury": 2,
    "Venus": 3,
    "Mars": 4,
    "Jupiter": 5,
    "Saturn": 6,
}


def get_house_number(planet_longitude, ascendant_longitude):
    """
    Calculate which house (1-12) a planet is in.
    Uses equal house system: each house is 30 degrees from ascendant.
    """
    diff = (planet_longitude - ascendant_longitude) % 360
    house = int(diff / 30) + 1
    return house


def get_planet_data(jd, planet_name, planet_idx, ascendant_lon=None):
    """Get full position data for a single planet."""
    lon = drik.sidereal_longitude(jd, planet_idx)
    sign_idx = int(lon / 30) % 12
    deg_in_sign = lon % 30

    result = {
        "planet": planet_name,
        "longitude": round(lon, 4),
        "sign": SIGNS[sign_idx],
        "sign_number": sign_idx + 1,
        "degrees_in_sign": round(deg_in_sign, 4),
    }

    if ascendant_lon is not None:
        result["house"] = get_house_number(lon, ascendant_lon)

    return result


def geocode_city(city_name):
    """Convert city name to lat, lon, timezone offset."""
    loc = _geocoder.geocode(city_name)
    if not loc:
        return None
    lat, lon = loc.latitude, loc.longitude
    tz_name = _tz_finder.timezone_at(lat=lat, lng=lon)
    if tz_name:
        tz_obj = pytz.timezone(tz_name)
        # Use standard offset (non-DST)
        std_offset = tz_obj.utcoffset(dt(2000, 1, 15)).total_seconds() / 3600
    else:
        std_offset = 0.0
    return {
        "city": city_name,
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "timezone_name": tz_name,
        "timezone_offset": std_offset,
    }


# ==========================================================
# API ENDPOINTS
# ==========================================================

from fastapi.responses import HTMLResponse, FileResponse


@app.get("/health")
def health():
    """Simple health check for connection testing (e.g. from Android emulator)."""
    return {"status": "ok", "message": "PyJHora API is running"}
import os

HOROSCOPE_APP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "horoscope_app")


@app.get("/", response_class=HTMLResponse)
def home():
    """Serve the Horoscope App if available, otherwise show API info."""
    index_path = os.path.join(HOROSCOPE_APP_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return """<html><body><h1>PyJHora Astrology API</h1>
    <p>Visit <a href='/docs'>/docs</a> for API documentation.</p>
    <p>Visit <a href='/app'>/app</a> for the Horoscope App.</p></body></html>"""


@app.get("/app", response_class=HTMLResponse)
def horoscope_app():
    """Serve the Horoscope App."""
    index_path = os.path.join(HOROSCOPE_APP_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<html><body><p>horoscope_app/index.html not found.</p></body></html>"


@app.get("/geocode")
def geocode(
    city: str = Query(..., description="City name with country, e.g. 'Chennai, India' or 'New York, USA'"),
):
    """
    Convert a city name to latitude, longitude, and timezone offset.
    Use this when you only have a city name and need lat/lon for other endpoints.

    Example: /geocode?city=Chennai, India
    Returns: {"latitude": 13.0721, "longitude": 80.2019, "timezone_offset": 5.5}
    """
    result = geocode_city(city)
    if result is None:
        return {"status": "error", "message": f"City '{city}' not found"}
    return {"status": "ok", "data": result}


@app.get("/planet-positions")
def planet_positions(
    year: int = Query(..., description="Birth year, e.g. 1968"),
    month: int = Query(..., description="Birth month, e.g. 10"),
    day: int = Query(..., description="Birth day, e.g. 6"),
    hour: int = Query(12, description="Birth hour (24h format), e.g. 5"),
    minute: int = Query(0, description="Birth minute, e.g. 35"),
    second: int = Query(0, description="Birth second, e.g. 0"),
    lat: float = Query(..., description="Latitude of birth place, e.g. 48.55"),
    lon: float = Query(..., description="Longitude of birth place, e.g. 3.30"),
    tz: float = Query(5.5, description="Timezone offset from UTC, e.g. 5.5 for India, 1.0 for France"),
):
    """
    Get planetary positions with HOUSE NUMBERS (1-12) for given birth details.

    Uses Lahiri Ayanamsa (sidereal) and Equal House system.
    Returns: Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn + Rahu, Ketu
    Each planet includes: longitude, sign, degrees_in_sign, house (1-12)
    """
    dob = drik.Date(year, month, day)
    tob = (hour, minute, second)
    place = drik.Place("BirthPlace", lat, lon, tz)
    jd = utils.julian_day_number(dob, tob)

    # Get ascendant (Lagna)
    asc_data = drik.ascendant(jd, place)
    # asc_data = [rasi, degrees_in_rasi, nakshatra, pada]
    asc_rasi = asc_data[0]
    asc_deg = asc_data[1]
    asc_longitude = asc_rasi * 30 + asc_deg

    ascendant_info = {
        "longitude": round(asc_longitude, 4),
        "sign": SIGNS[asc_rasi],
        "sign_number": asc_rasi + 1,
        "degrees_in_sign": round(asc_deg, 4),
    }

    # Get planet positions with house numbers
    planets = []
    for planet_name, planet_idx in PLANET_INDICES.items():
        planets.append(get_planet_data(jd, planet_name, planet_idx, asc_longitude))

    # Rahu and Ketu from planetary_positions
    pp = drik.planetary_positions(jd, place)
    if len(pp) >= 9:
        # Rahu
        rahu_rasi, rahu_deg = pp[7][0], pp[7][1]
        rahu_lon = rahu_rasi * 30 + rahu_deg
        rahu_house = get_house_number(rahu_lon, asc_longitude)
        planets.append({
            "planet": "Rahu",
            "longitude": round(rahu_lon, 4),
            "sign": SIGNS[rahu_rasi],
            "sign_number": rahu_rasi + 1,
            "degrees_in_sign": round(rahu_deg, 4),
            "house": rahu_house,
        })
        # Ketu
        ketu_rasi, ketu_deg = pp[8][0], pp[8][1]
        ketu_lon = ketu_rasi * 30 + ketu_deg
        ketu_house = get_house_number(ketu_lon, asc_longitude)
        planets.append({
            "planet": "Ketu",
            "longitude": round(ketu_lon, 4),
            "sign": SIGNS[ketu_rasi],
            "sign_number": ketu_rasi + 1,
            "degrees_in_sign": round(ketu_deg, 4),
            "house": ketu_house,
        })

    return {
        "status": "ok",
        "input": {
            "date": f"{year:04d}-{month:02d}-{day:02d}",
            "time": f"{hour:02d}:{minute:02d}:{second:02d}",
            "latitude": lat,
            "longitude": lon,
            "timezone": tz,
            "ayanamsa": "Lahiri",
            "house_system": "Equal",
        },
        "ascendant": ascendant_info,
        "planet_positions": planets,
    }


@app.get("/panchang")
def panchang(
    year: int = Query(..., description="Year"),
    month: int = Query(..., description="Month"),
    day: int = Query(..., description="Day"),
    hour: int = Query(12, description="Hour"),
    minute: int = Query(0, description="Minute"),
    second: int = Query(0, description="Second"),
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    tz: float = Query(5.5, description="Timezone offset"),
):
    """
    Get panchang data (tithi, nakshatra, yoga, karana) for given date/time/place.
    """
    dob = drik.Date(year, month, day)
    tob = (hour, minute, second)
    place = drik.Place("Query", lat, lon, tz)
    jd = utils.julian_day_number(dob, tob)

    result = {"status": "ok", "input": {
        "date": f"{year:04d}-{month:02d}-{day:02d}",
        "time": f"{hour:02d}:{minute:02d}:{second:02d}",
    }}

    try:
        result["tithi"] = str(drik.tithi(jd, place))
    except Exception as e:
        result["tithi"] = f"Error: {e}"
    try:
        result["nakshatra"] = str(drik.nakshatra(jd, place))
    except Exception as e:
        result["nakshatra"] = f"Error: {e}"
    try:
        result["yoga"] = str(drik.yogam(jd, place))
    except Exception as e:
        result["yoga"] = f"Error: {e}"
    try:
        result["karana"] = str(drik.karana(jd, place))
    except Exception as e:
        result["karana"] = f"Error: {e}"

    return result


@app.get("/positions-28-years")
def positions_28_years(
    year: int = Query(..., description="Birth year"),
    month: int = Query(..., description="Birth month"),
    day: int = Query(..., description="Birth day"),
    hour: int = Query(12, description="Birth hour"),
    minute: int = Query(0, description="Birth minute"),
    second: int = Query(0, description="Birth second"),
    lat: float = Query(..., description="Latitude of birth place"),
    lon: float = Query(..., description="Longitude of birth place"),
    tz: float = Query(5.5, description="Timezone offset"),
    interval: str = Query("yearly", description="'yearly' (29 points) or 'monthly' (~336 points)"),
):
    """
    Generate planetary positions for 28 years from date of birth.
    Each data point includes house number (1-12) for every planet.

    Chethan's requirement:
    "pass date/time/location and it generates planetary position for 28 years from DOB"
    """
    tob = (hour, minute, second)
    place = drik.Place("BirthPlace", lat, lon, tz)

    positions_list = []

    if interval == "monthly":
        for month_offset in range(28 * 12 + 1):
            target_year = year + (month + month_offset - 1) // 12
            target_month = (month + month_offset - 1) % 12 + 1
            target_day = min(day, 28)
            target_dob = drik.Date(target_year, target_month, target_day)
            target_jd = utils.julian_day_number(target_dob, tob)

            # Get ascendant for house calculation
            asc_data = drik.ascendant(target_jd, place)
            asc_longitude = asc_data[0] * 30 + asc_data[1]

            entry = {
                "date": f"{target_year:04d}-{target_month:02d}-{target_day:02d}",
                "planets": {},
            }
            for planet_name, planet_idx in PLANET_INDICES.items():
                data = get_planet_data(target_jd, planet_name, planet_idx, asc_longitude)
                entry["planets"][planet_name] = {
                    "longitude": data["longitude"],
                    "sign": data["sign"],
                    "degrees_in_sign": data["degrees_in_sign"],
                    "house": data["house"],
                }
            positions_list.append(entry)
    else:
        for yr_offset in range(29):
            target_year = year + yr_offset
            target_dob = drik.Date(target_year, month, day)
            target_jd = utils.julian_day_number(target_dob, tob)

            asc_data = drik.ascendant(target_jd, place)
            asc_longitude = asc_data[0] * 30 + asc_data[1]

            entry = {
                "date": f"{target_year:04d}-{month:02d}-{day:02d}",
                "planets": {},
            }
            for planet_name, planet_idx in PLANET_INDICES.items():
                data = get_planet_data(target_jd, planet_name, planet_idx, asc_longitude)
                entry["planets"][planet_name] = {
                    "longitude": data["longitude"],
                    "sign": data["sign"],
                    "degrees_in_sign": data["degrees_in_sign"],
                    "house": data["house"],
                }
            positions_list.append(entry)

    return {
        "status": "ok",
        "input": {
            "date_of_birth": f"{year:04d}-{month:02d}-{day:02d}",
            "time_of_birth": f"{hour:02d}:{minute:02d}:{second:02d}",
            "latitude": lat,
            "longitude": lon,
            "timezone": tz,
            "interval": interval,
        },
        "total_data_points": len(positions_list),
        "positions": positions_list,
    }


@app.get("/transits")
def transits(
    year: int = Query(..., description="Year to scan, e.g. 2026"),
    lat: float = Query(28.6139, description="Latitude (default: Delhi)"),
    lon: float = Query(77.2090, description="Longitude (default: Delhi)"),
    tz: float = Query(5.5, description="Timezone offset (default: India)"),
):
    """
    Detect all planetary sign transitions for a given year.

    Scans the entire year day by day. Whenever ANY planet changes zodiac sign,
    it records:
    - Date and time of the transition
    - Which planet changed
    - From which sign -> To which sign
    - Positions of ALL other planets at that exact moment

    Only changes are recorded. Pass just the year.
    """
    place = drik.Place("Location", lat, lon, tz)
    tob = (0, 0, 0)  # midnight

    # Correct planet indices (Swiss Ephemeris order)
    planet_map = {
        "Sun": 0, "Moon": 1, "Mercury": 2, "Venus": 3,
        "Mars": 4, "Jupiter": 5, "Saturn": 6,
    }

    transition_records = []

    # --- Helper: get sign index for a planet at a given Julian day ---
    def _sign_at(jd, pidx):
        lon_val = drik.sidereal_longitude(jd, pidx)
        return int(lon_val / 30) % 12

    # --- Helper: binary search to find exact minute of sign change ---
    def _find_exact_transition(dt_before, dt_after, pidx, expected_old_sign):
        """
        Binary search between dt_before (planet in old sign) and dt_after
        (planet in new sign) to find the exact minute of transition.
        Returns a datetime accurate to ~1 minute.
        """
        lo = dt_before
        hi = dt_after
        # Binary search down to 1-minute precision (6 hrs = 360 mins, log2(360)~9 iterations)
        for _ in range(15):
            mid = lo + (hi - lo) / 2
            mid_dob = drik.Date(mid.year, mid.month, mid.day)
            mid_tob = (mid.hour, mid.minute, 0)
            mid_jd = utils.julian_day_number(mid_dob, mid_tob)
            mid_sign = _sign_at(mid_jd, pidx)
            if mid_sign == expected_old_sign:
                lo = mid  # still in old sign, move forward
            else:
                hi = mid  # already in new sign, move backward
            if (hi - lo).total_seconds() <= 60:
                break
        return hi  # first moment in new sign

    # --- Helper: collect all planet positions + houses at a given datetime ---
    def _snapshot(at_dt):
        snap_dob = drik.Date(at_dt.year, at_dt.month, at_dt.day)
        snap_tob = (at_dt.hour, at_dt.minute, 0)
        snap_jd = utils.julian_day_number(snap_dob, snap_tob)
        # Ascendant
        try:
            asc_data = drik.ascendant(snap_jd, place)
            asc_lon = asc_data[0] * 30 + asc_data[1]
        except Exception:
            asc_lon = None
        # Planet positions
        positions = {}
        for pn, pi in planet_map.items():
            lon_val = drik.sidereal_longitude(snap_jd, pi)
            sign_idx = int(lon_val / 30) % 12
            entry = {
                "longitude": round(lon_val, 4),
                "sign": SIGNS[sign_idx],
                "degrees_in_sign": round(lon_val % 30, 4),
            }
            if asc_lon is not None:
                entry["house"] = get_house_number(lon_val, asc_lon)
            positions[pn] = entry
        return positions, asc_lon

    # Get initial positions on Jan 1
    start_dob = drik.Date(year, 1, 1)
    start_jd = utils.julian_day_number(start_dob, tob)

    prev_signs = {}
    for pname, pidx in planet_map.items():
        prev_signs[pname] = _sign_at(start_jd, pidx)

    # Scan the year in 6-hour coarse intervals, then binary-search for exact minute
    start_date = dt(year, 1, 1)
    end_date = dt(year, 12, 31, 18, 0, 0)
    prev_dt = start_date
    current = start_date + timedelta(hours=6)

    while current <= end_date:
        check_dob = drik.Date(current.year, current.month, current.day)
        check_tob = (current.hour, current.minute, 0)
        check_jd = utils.julian_day_number(check_dob, check_tob)

        # Check each planet for sign change in this 6-hour window
        for pname, pidx in planet_map.items():
            cur_sign = _sign_at(check_jd, pidx)
            if cur_sign != prev_signs[pname]:
                # Binary search to find exact transition minute
                exact_dt = _find_exact_transition(prev_dt, current, pidx, prev_signs[pname])
                # Round to nearest minute
                exact_dt = exact_dt.replace(second=0, microsecond=0)

                from_sign = SIGNS[prev_signs[pname]]
                to_sign = SIGNS[cur_sign]

                # Get snapshot of ALL planets at the exact transition moment
                all_positions, asc_lon = _snapshot(exact_dt)

                record = {
                    "date": exact_dt.strftime("%Y-%m-%d"),
                    "time": exact_dt.strftime("%H:%M"),
                    "planet": pname,
                    "from_sign": from_sign,
                    "to_sign": to_sign,
                    "all_planet_positions": all_positions,
                }
                if asc_lon is not None:
                    record["ascendant"] = {
                        "longitude": round(asc_lon, 4),
                        "sign": SIGNS[int(asc_lon / 30) % 12],
                    }
                transition_records.append(record)

                prev_signs[pname] = cur_sign

        # Update for next iteration
        prev_dt = current
        current += timedelta(hours=6)

    # Sort by exact datetime
    transition_records.sort(key=lambda r: r["date"] + " " + r["time"])

    return {
        "status": "ok",
        "input": {
            "year": year,
            "latitude": lat,
            "longitude": lon,
            "timezone": tz,
        },
        "note": "Times are accurate to ~1 minute (binary search within 6-hour windows)",
        "total_transitions": len(transition_records),
        "transitions": transition_records,
    }


# ==========================================================
# VIMSHOTTARI DASHA ENDPOINT
# ==========================================================

from jhora.horoscope.dhasa.graha import vimsottari

# PyJHora planet index -> name mapping for dashas
DASHA_PLANET_NAMES = {
    0: "Sun (Surya)",
    1: "Moon (Chandra)",
    2: "Mars (Mangal)",
    3: "Mercury (Budha)",
    4: "Jupiter (Guru)",
    5: "Venus (Shukra)",
    6: "Saturn (Shani)",
    7: "Rahu",
    8: "Ketu",
}

# Standard Vimshottari durations in years
DASHA_YEARS = {
    0: 6,   # Sun
    1: 10,  # Moon
    2: 7,   # Mars
    3: 17,  # Mercury
    4: 16,  # Jupiter
    5: 20,  # Venus
    6: 19,  # Saturn
    7: 18,  # Rahu
    8: 7,   # Ketu
}


@app.get("/dasha")
def dasha(
    year: int = Query(..., description="Birth year, e.g. 1968"),
    month: int = Query(..., description="Birth month, e.g. 10"),
    day: int = Query(..., description="Birth day, e.g. 6"),
    hour: int = Query(12, description="Birth hour (24h format)"),
    minute: int = Query(0, description="Birth minute"),
    second: int = Query(0, description="Birth second"),
    lat: float = Query(..., description="Latitude of birth place"),
    lon: float = Query(..., description="Longitude of birth place"),
    tz: float = Query(5.5, description="Timezone offset from UTC"),
):
    """
    Compute Vimshottari Mahadasha + Antardasha for 120 years from birth.

    Returns 9 Mahadashas (major periods) each containing 9 Antardashas (sub-periods).
    Standard sequence: Ketu(7yr) -> Venus(20) -> Sun(6) -> Moon(10) -> Mars(7) ->
                       Rahu(18) -> Jupiter(16) -> Saturn(19) -> Mercury(17) = 120 years.

    The starting Mahadasha depends on the Moon's Nakshatra at birth.
    """
    dob = drik.Date(year, month, day)
    tob = (hour, minute, second)
    place = drik.Place("BirthPlace", lat, lon, tz)
    jd = utils.julian_day_number(dob, tob)

    try:
        vim_bal, dhasa_bukthi = vimsottari.get_vimsottari_dhasa_bhukthi(
            jd, place,
            include_antardhasa=True,
            dhasa_starting_planet=1,  # Moon-based (standard)
        )
    except Exception as e:
        return {"status": "error", "message": f"Dasha calculation failed: {e}"}

    # Organize into Mahadasha -> Antardasha structure
    mahadashas = []
    current_maha = None

    for entry in dhasa_bukthi:
        maha_lord = entry[0]
        bhukthi_lord = entry[1]
        start_date_str = entry[2] if len(entry) > 2 else "unknown"

        maha_name = DASHA_PLANET_NAMES.get(maha_lord, f"Planet-{maha_lord}")
        bhukthi_name = DASHA_PLANET_NAMES.get(bhukthi_lord, f"Planet-{bhukthi_lord}")

        # Check if we're starting a new Mahadasha
        if current_maha is None or current_maha["lord_id"] != maha_lord:
            # Start new Mahadasha
            current_maha = {
                "lord_id": maha_lord,
                "lord": maha_name,
                "total_years": DASHA_YEARS.get(maha_lord, "?"),
                "start_date": start_date_str,
                "antardashas": [],
            }
            mahadashas.append(current_maha)

        # Add Antardasha
        current_maha["antardashas"].append({
            "lord_id": bhukthi_lord,
            "lord": bhukthi_name,
            "start_date": start_date_str,
        })

    # Calculate end dates for each antardasha (start of next = end of current)
    all_antardashas = []
    for maha in mahadashas:
        all_antardashas.extend(maha["antardashas"])

    for i, ad in enumerate(all_antardashas):
        if i + 1 < len(all_antardashas):
            ad["end_date"] = all_antardashas[i + 1]["start_date"]
        else:
            ad["end_date"] = "end of 120-year cycle"

    # Also set end_date for each Mahadasha
    for i, maha in enumerate(mahadashas):
        if i + 1 < len(mahadashas):
            maha["end_date"] = mahadashas[i + 1]["start_date"]
        else:
            maha["end_date"] = "end of 120-year cycle"

    return {
        "status": "ok",
        "input": {
            "date_of_birth": f"{year:04d}-{month:02d}-{day:02d}",
            "time_of_birth": f"{hour:02d}:{minute:02d}:{second:02d}",
            "latitude": lat,
            "longitude": lon,
            "timezone": tz,
        },
        "dasha_balance_at_birth_days": round(vim_bal, 2) if isinstance(vim_bal, (int, float)) else str(vim_bal),
        "note": "Vimshottari Dasha based on Moon's Nakshatra at birth. 9 Mahadashas = 120 years total.",
        "total_mahadashas": len(mahadashas),
        "mahadashas": mahadashas,
    }


# ==========================================================
# PANCHANG DETAILED ENDPOINT
# ==========================================================

TITHI_NAMES = [
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima",
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Amavasya",
]

PAKSHA_NAMES = ["Shukla Paksha (Waxing)", "Krishna Paksha (Waning)"]

NAKSHATRA_NAMES = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira",
    "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha",
    "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati",
    "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha",
    "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
]

VAARA_NAMES = [
    "Ravivara (Sunday)", "Somavara (Monday)", "Mangalavara (Tuesday)",
    "Budhavara (Wednesday)", "Guruvara (Thursday)", "Shukravara (Friday)",
    "Shanivara (Saturday)",
]

LUNAR_MONTH_NAMES = [
    "Chaitra", "Vaishakha", "Jyeshtha", "Ashadha", "Shravana",
    "Bhadrapada", "Ashvina", "Kartika", "Margashirsha", "Pushya/Pausa",
    "Magha", "Phalguna",
]

RITU_NAMES = [
    "Vasanta (Spring)", "Grishma (Summer)", "Varsha (Monsoon)",
    "Sharad (Autumn)", "Hemanta (Pre-Winter)", "Shishira (Winter)",
]

SAMVATSARA_NAMES = [
    "Prabhava", "Vibhava", "Shukla", "Pramodoota", "Prajothpatti",
    "Angirasa", "Srimukha", "Bhava", "Yuva", "Dhatu",
    "Eeshwara", "Bahudhanya", "Pramathi", "Vikrama", "Vrisha",
    "Chitrabhanu", "Svabhanu", "Tarana", "Parthiva", "Vyaya",
    "Sarvajith", "Sarvadhari", "Virodhi", "Vikruti", "Khara",
    "Nandana", "Vijaya", "Jaya", "Manmatha", "Durmukhi",
    "Hevilambi", "Vilambi", "Vikari", "Sharvari", "Plava",
    "Shubhakrutu", "Shobhakrutu", "Krodhi", "Vishvavasu", "Parabhava",
    "Plavanga", "Kilaka", "Saumya", "Sadharana", "Virodhikrutu",
    "Pareedhavi", "Pramadicha", "Ananda", "Rakshasa", "Nala",
    "Pingala", "Kalayukthi", "Siddharthi", "Raudri", "Durmathi",
    "Dundubhi", "Rudhirodgari", "Raktakshi", "Krodhana", "Akshaya",
]


def _safe_call(func, *args, **kwargs):
    """Safely call a PyJHora function, return None on error."""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        return f"Error: {e}"


def _float_hours_to_time(fh):
    """Convert float hours (e.g. 7.05) to time string 'HH:MM'."""
    try:
        fh = float(fh)
        if fh < 0:
            fh += 24  # previous day adjustment
        if fh >= 24:
            fh -= 24
        h = int(fh)
        m = int((fh - h) * 60)
        return f"{h:02d}:{m:02d}"
    except Exception:
        return str(fh)


@app.get("/panchang-detailed")
def panchang_detailed(
    year: int = Query(..., description="Year, e.g. 2026"),
    month: int = Query(..., description="Month, e.g. 2"),
    day: int = Query(..., description="Day, e.g. 16"),
    hour: int = Query(12, description="Hour (24h format)"),
    minute: int = Query(0, description="Minute"),
    second: int = Query(0, description="Second"),
    lat: float = Query(..., description="Latitude of location"),
    lon: float = Query(..., description="Longitude of location"),
    tz: float = Query(5.5, description="Timezone offset from UTC"),
):
    """
    Detailed Panchang data for a given date/time/location.

    Returns:
    1. Sunrise / Sunset
    2. Moonrise / Moonset
    3. Tithi, Nakshatra, Vaara
    4. Rahu Kaal
    5. Month, Season (Ritu), Samvatsara
    """
    dob = drik.Date(year, month, day)
    tob = (hour, minute, second)
    place = drik.Place("Location", lat, lon, tz)
    jd = utils.julian_day_number(dob, tob)

    result = {
        "status": "ok",
        "input": {
            "date": f"{year:04d}-{month:02d}-{day:02d}",
            "time": f"{hour:02d}:{minute:02d}:{second:02d}",
            "latitude": lat,
            "longitude": lon,
            "timezone": tz,
        },
    }

    # 1. Sunrise / Sunset
    sunrise_data = _safe_call(drik.sunrise, jd, place)
    sunset_data = _safe_call(drik.sunset, jd, place)
    if isinstance(sunrise_data, list) and len(sunrise_data) >= 2:
        result["sunrise"] = str(sunrise_data[1])
    else:
        result["sunrise"] = str(sunrise_data)

    if isinstance(sunset_data, list) and len(sunset_data) >= 2:
        result["sunset"] = str(sunset_data[1])
    else:
        result["sunset"] = str(sunset_data)

    # 2. Moonrise / Moonset
    moonrise_data = _safe_call(drik.moonrise, jd, place)
    moonset_data = _safe_call(drik.moonset, jd, place)
    if isinstance(moonrise_data, list) and len(moonrise_data) >= 2:
        result["moonrise"] = str(moonrise_data[1])
    else:
        result["moonrise"] = str(moonrise_data)

    if isinstance(moonset_data, list) and len(moonset_data) >= 2:
        result["moonset"] = str(moonset_data[1])
    else:
        result["moonset"] = str(moonset_data)

    # 3a. Tithi
    tithi_data = _safe_call(drik.tithi, jd, place)
    if isinstance(tithi_data, (list, tuple)) and len(tithi_data) >= 1:
        tithi_num = int(tithi_data[0])
        paksha = PAKSHA_NAMES[0] if tithi_num <= 15 else PAKSHA_NAMES[1]
        tithi_name = TITHI_NAMES[tithi_num - 1] if 1 <= tithi_num <= 30 else f"Tithi-{tithi_num}"
        result["tithi"] = {
            "number": tithi_num,
            "name": tithi_name,
            "paksha": paksha,
        }
        if len(tithi_data) >= 3:
            result["tithi"]["start_time"] = _float_hours_to_time(tithi_data[1])
            result["tithi"]["end_time"] = _float_hours_to_time(tithi_data[2])
    else:
        result["tithi"] = str(tithi_data)

    # 3b. Nakshatra
    nakshatra_data = _safe_call(drik.nakshatra, jd, place)
    if isinstance(nakshatra_data, (list, tuple)) and len(nakshatra_data) >= 1:
        nak_num = int(nakshatra_data[0])
        nak_name = NAKSHATRA_NAMES[nak_num - 1] if 1 <= nak_num <= 27 else f"Nakshatra-{nak_num}"
        result["nakshatra"] = {
            "number": nak_num,
            "name": nak_name,
        }
        if len(nakshatra_data) >= 2:
            result["nakshatra"]["pada"] = int(nakshatra_data[1])
        if len(nakshatra_data) >= 4:
            result["nakshatra"]["start_time"] = _float_hours_to_time(nakshatra_data[2])
            result["nakshatra"]["end_time"] = _float_hours_to_time(nakshatra_data[3])
    else:
        result["nakshatra"] = str(nakshatra_data)

    # 3c. Vaara (Day of week)
    vaara_data = _safe_call(drik.vaara, jd)
    if isinstance(vaara_data, int) and 0 <= vaara_data <= 6:
        result["vaara"] = {
            "number": vaara_data,
            "name": VAARA_NAMES[vaara_data],
        }
    else:
        result["vaara"] = str(vaara_data)

    # 4. Rahu Kaal
    rahu_data = _safe_call(drik.raahu_kaalam, jd, place)
    if isinstance(rahu_data, (list, tuple)) and len(rahu_data) >= 2:
        result["rahu_kaal"] = {
            "start": str(rahu_data[0]),
            "end": str(rahu_data[1]),
        }
    else:
        result["rahu_kaal"] = str(rahu_data)

    # Also get Yamagandam and Gulikai for completeness
    yama_data = _safe_call(drik.trikalam, jd, place, 'yamagandam')
    if isinstance(yama_data, (list, tuple)) and len(yama_data) >= 2:
        result["yamagandam"] = {
            "start": str(yama_data[0]),
            "end": str(yama_data[1]),
        }

    gulikai_data = _safe_call(drik.trikalam, jd, place, 'gulikai')
    if isinstance(gulikai_data, (list, tuple)) and len(gulikai_data) >= 2:
        result["gulikai_kaal"] = {
            "start": str(gulikai_data[0]),
            "end": str(gulikai_data[1]),
        }

    # 5a. Lunar Month
    month_data = _safe_call(drik.lunar_month, jd, place)
    if isinstance(month_data, (list, tuple)) and len(month_data) >= 1:
        m_idx = int(month_data[0])
        m_name = LUNAR_MONTH_NAMES[m_idx - 1] if 1 <= m_idx <= 12 else f"Month-{m_idx}"
        result["lunar_month"] = {
            "number": m_idx,
            "name": m_name,
        }
        if len(month_data) >= 2:
            result["lunar_month"]["is_leap_month"] = bool(month_data[1])
    else:
        result["lunar_month"] = str(month_data)

    # 5b. Season (Ritu)
    if isinstance(month_data, (list, tuple)) and len(month_data) >= 1:
        ritu_data = _safe_call(drik.ritu, int(month_data[0]))
        if isinstance(ritu_data, int) and 0 <= ritu_data <= 5:
            result["ritu"] = {
                "number": ritu_data,
                "name": RITU_NAMES[ritu_data],
            }
        else:
            result["ritu"] = str(ritu_data)
    else:
        result["ritu"] = "Could not determine (depends on lunar month)"

    # 5c. Samvatsara (60-year cycle)
    # Try multiple approaches for samvatsara
    samvat_result = None

    # Approach 1: drik.samvatsara with Date object
    samvat_data = _safe_call(drik.samvatsara, dob, place)
    if isinstance(samvat_data, int):
        samvat_result = samvat_data

    # Approach 2: Calculate from Jovian year (Jupiter's 12-year cycle * 5 = 60 year cycle)
    if samvat_result is None:
        # Standard calculation: (year + 11) % 60 gives approximate samvatsara
        # This is simplified but commonly used
        idx = (year + 11) % 60
        samvat_result = idx

    if samvat_result is not None:
        idx = samvat_result % 60
        result["samvatsara"] = {
            "number": idx + 1,
            "name": SAMVATSARA_NAMES[idx] if idx < len(SAMVATSARA_NAMES) else f"Samvatsara-{idx}",
        }
    else:
        result["samvatsara"] = "Could not determine"

    return result
