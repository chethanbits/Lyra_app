# app.py
"""
Lyra Engine API (FastAPI) — minimal backend wrapper for the frontend

What this provides:
- /health                   -> sanity check
- /day                      -> DayResult JSON (panchang + score + summary)
- /range                    -> list[DayResult] for a date range (inclusive)
- /heatmap                  -> lightweight list for calendar heatmap
- /p/day                    -> profile day (birth chart + Tara Bala / personal alignment)
- /p/range                  -> profile range (same for date range)
- /config                   -> tells which weights file is loaded (debug)

Assumptions:
- engine.py (your typed stub) exists in the same folder and is implemented.
- weights file exists (default: weights_balanced.yaml or weights.json).
- Optional: your text engine is integrated inside compute_alignment_score()
  OR you can add summary generation after scoring (see TODO below).

Install:
  pip install fastapi uvicorn pyyaml

Run:
  uvicorn app:app --reload --host 0.0.0.0 --port 8000

Example call:
  GET /day?date=2026-03-01&lat=28.6139&lon=77.2090&tz=5.5&region=NORTH_INDIA
"""

from __future__ import annotations

import os
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Set Swiss Ephemeris path before jhora/engine are imported
_ephe = os.environ.get("SWISSEPH_EPHE_PATH") or str(Path(__file__).resolve().parent / "ephe")
if Path(_ephe).is_dir():
    import shutil
    import sys
    import swisseph as _swe
    _swe.set_ephe_path(_ephe)
    for _p in sys.path:
        _jhora_ephe = Path(_p) / "jhora" / "data" / "ephe"
        if _jhora_ephe.is_dir():
            for _f in Path(_ephe).glob("*.se1"):
                _dest = _jhora_ephe / _f.name
                if not _dest.exists() or _dest.stat().st_size != _f.stat().st_size:
                    shutil.copy2(_f, _dest)
            break

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import your engine layer
from engine import (
    Place,
    EngineSettings,
    RegionMode,
    AnchorMode,
    Band,
    EngineError,
    load_weights_config,
    compute_day,
    compute_range,
    compute_heatmap,
)
import engine_profile as profile_engine
from profiles import BirthDetails, Place as ProfilePlace
from cache import TTLCache, build_cache_key

# Optional: read from preloaded SQLite store first (env var or auto if DB exists)
_default_db = Path(__file__).resolve().parent / "lyra_preloaded.db"
USE_PRELOADED_STORE = (
    os.environ.get("LYRA_USE_STORE", "").strip().lower() in ("1", "true", "yes")
    or _default_db.exists()
)
LYRA_DB_PATH = os.environ.get("LYRA_DB_PATH", "")
if USE_PRELOADED_STORE:
    from store import get_day as store_get_day, get_range as store_get_range, get_heatmap as store_get_heatmap, get_nearest_preloaded_place as store_get_nearest_place
    _db_path = LYRA_DB_PATH or str(_default_db)
else:
    _db_path = ""

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

# Choose default weights file (can be overridden by env var)
DEFAULT_WEIGHTS_PATH = os.environ.get("LYRA_WEIGHTS_PATH", "weights_balanced.yaml")

# Ayanamsa default (pass-through string to PyJHora; your engine handles it)
DEFAULT_AYANAMSA = os.environ.get("LYRA_AYANAMSA_MODE", "LAHIRI")

# Anchor default
DEFAULT_ANCHOR = os.environ.get("LYRA_ANCHOR", "SUNRISE").upper()

# Load weights once at startup (config-driven tuning)
try:
    WEIGHTS = load_weights_config(DEFAULT_WEIGHTS_PATH)
except Exception as e:
    # Fail loudly: if weights missing, API is unusable
    raise RuntimeError(f"Failed to load weights from {DEFAULT_WEIGHTS_PATH}: {e}") from e

# Cache for profile endpoints (Tara Bala / personal alignment)
PROFILE_CACHE = TTLCache(max_items=20000, ttl_seconds=24 * 3600)


# ------------------------------------------------------------
# App
# ------------------------------------------------------------

app = FastAPI(
    title="Lyra Engine API",
    version="0.1.0",
    description="PyJHora-based Panchang + deterministic scoring API for Lyra frontend",
)

# Allow frontend (Vite dev server, Android emulator, Vercel preview/production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> Dict[str, Any]:
    """Root: point to health and docs."""
    return {
        "app": "Lyra Engine API",
        "docs": "/docs",
        "health": "/health",
        "day": "/day?date=YYYY-MM-DD&lat=...&lon=...&tz=5.5",
        "p/day": "/p/day?date=...&lat=...&birth_date=...&birth_time=...&pob_lat=...",
    }


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def parse_date(d: str) -> date:
    try:
        return datetime.strptime(d, "%Y-%m-%d").date()
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {d}. Expected YYYY-MM-DD.")


def ensure_lat_lon(lat: float, lon: float) -> None:
    if not (-90.0 <= lat <= 90.0):
        raise HTTPException(status_code=400, detail=f"Invalid latitude: {lat}")
    if not (-180.0 <= lon <= 180.0):
        raise HTTPException(status_code=400, detail=f"Invalid longitude: {lon}")


def ensure_tz(tz: float) -> None:
    # Rough bounds: -12..+14 typical
    if not (-14.0 <= tz <= 14.0):
        raise HTTPException(status_code=400, detail=f"Invalid timezone offset: {tz}. Expected -14..+14.")


def make_settings(region: str, anchor: str, ayanamsa: str) -> EngineSettings:
    try:
        region_mode = RegionMode(region.upper())
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid region: {region}. Use NORTH_INDIA or SOUTH_INDIA.")

    try:
        anchor_mode = AnchorMode(anchor.upper())
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid anchor: {anchor}. Use SUNRISE or NOW.")

    return EngineSettings(
        region_mode=region_mode,
        anchor=anchor_mode,
        ayanamsa_mode=ayanamsa,
    )


def dataclass_to_dict(obj: Any) -> Any:
    """
    Convert nested dataclasses (engine.py) to JSON-serializable dicts.
    Works for enums, lists, dicts, and dataclasses.
    """
    from dataclasses import is_dataclass, asdict

    if obj is None:
        return None

    # Enums -> value
    if hasattr(obj, "value") and obj.__class__.__name__.endswith("Mode") or obj.__class__.__name__ in {"Band", "RegionMode", "AnchorMode"}:
        try:
            return obj.value
        except Exception:
            pass

    if isinstance(obj, (str, int, float, bool)):
        return obj

    if isinstance(obj, dict):
        return {str(k): dataclass_to_dict(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [dataclass_to_dict(x) for x in obj]

    if is_dataclass(obj):
        return dataclass_to_dict(asdict(obj))

    return obj


def engine_error_to_http(e: Exception) -> HTTPException:
    if isinstance(e, EngineError):
        return HTTPException(
            status_code=400,
            detail={"code": getattr(e.code, "value", str(e.code)), "message": e.message, "details": e.details},
        )
    return HTTPException(status_code=500, detail=str(e))


def _day_response_from_store_row(
    row: Dict[str, Any],
    lat: float,
    lon: float,
    tz: float,
    place_name: Optional[str],
    place_used: Optional[str] = None,
) -> Dict[str, Any]:
    """Build /day response dict from a store row (same shape as DayResult serialization)."""
    panchanga = row.get("panchanga_json") or {}
    summary = row.get("summary_json") or []
    # Sanitize stored panchanga: fix invalid ends_at (e.g. "-992:-2") and karana "-1"
    if isinstance(panchanga, dict):
        import re
        for key in ("tithi", "nakshatra", "yoga", "karana"):
            item = panchanga.get(key)
            if isinstance(item, dict) and "ends_at" in item:
                et = str(item["ends_at"])
                if not re.match(r"^\d{1,2}:\d{2}$", et) or int(et.split(":")[0]) > 23:
                    item["ends_at"] = "00:00"
            if key == "karana" and isinstance(item, dict) and "name" in item:
                n = str(item["name"]).strip()
                if n in ("-1", "0", "") or (n.isdigit() and (int(n) < 1 or int(n) > 11)):
                    item["name"] = "Bava"
    out = {
        "date": row["date"],
        "place": {"lat": lat, "lon": lon, "tz": tz, "name": place_name},
        "anchor": "SUNRISE",
        "panchanga": panchanga,
        "score": {
            "alignment_score": row["score"],
            "band": row["band"],
            "breakdown": [],
            "summary": summary,
        },
    }
    if place_used is not None:
        out["place_used"] = place_used
    return out


# Preloaded city names by place_id (for place_used in response when using nearest-city fallback)
PRELOADED_PLACE_NAMES = {
    "28.61_77.21_5.5": "Delhi",
    "19.08_72.88_5.5": "Mumbai",
    "13.08_80.27_5.5": "Chennai",
    "12.97_77.59_5.5": "Bangalore",
    "18.52_73.86_5.5": "Pune",
    "17.39_78.49_5.5": "Hyderabad",
    "22.57_88.36_5.5": "Kolkata",
    "25.32_82.97_5.5": "Varanasi",
    "26.91_75.79_5.5": "Jaipur",
    "23.02_72.57_5.5": "Ahmedabad",
}


# ------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------

@app.get("/health")
def health() -> Dict[str, Any]:
    out = {
        "status": "ok",
        "weights_loaded": True,
        "weights_path": DEFAULT_WEIGHTS_PATH,
        "ayanamsa_default": DEFAULT_AYANAMSA,
        "anchor_default": DEFAULT_ANCHOR,
    }
    if USE_PRELOADED_STORE and _db_path:
        out["store_enabled"] = True
        out["store_path"] = _db_path
    else:
        out["store_enabled"] = False
    return out


@app.get("/config")
def config() -> Dict[str, Any]:
    # Useful for debugging what is currently active
    return {
        "weights_path": DEFAULT_WEIGHTS_PATH,
        "base_score": WEIGHTS.base_score,
        "rahu_day_penalty": WEIGHTS.rahu_day_penalty,
        "bands": {k.value if hasattr(k, "value") else str(k): v for k, v in WEIGHTS.bands.items()},
    }


# Built-in fallback when Nominatim is unreachable (502/network). Keys lowercased for match.
GEOCODE_FALLBACK = {
    "delhi": (28.6139, 77.209, 5.5, "Delhi, India"),
    "mumbai": (19.0760, 72.8777, 5.5, "Mumbai, India"),
    "bangalore": (12.9716, 77.5946, 5.5, "Bangalore, India"),
    "bengaluru": (12.9716, 77.5946, 5.5, "Bangalore, India"),
    "chennai": (13.0827, 80.2707, 5.5, "Chennai, India"),
    "kolkata": (22.5726, 88.3639, 5.5, "Kolkata, India"),
    "hyderabad": (17.3850, 78.4867, 5.5, "Hyderabad, India"),
    "pune": (18.5204, 73.8567, 5.5, "Pune, India"),
    "ahmedabad": (23.0225, 72.5714, 5.5, "Ahmedabad, India"),
    "jaipur": (26.9124, 75.7873, 5.5, "Jaipur, India"),
    "varanasi": (25.3176, 82.9739, 5.5, "Varanasi, India"),
    "lucknow": (26.8467, 80.9462, 5.5, "Lucknow, India"),
    "kochi": (9.9312, 76.2673, 5.5, "Kochi, India"),
    "cochin": (9.9312, 76.2673, 5.5, "Kochi, India"),
    "trivandrum": (8.5241, 76.9366, 5.5, "Thiruvananthapuram, India"),
    "thiruvananthapuram": (8.5241, 76.9366, 5.5, "Thiruvananthapuram, India"),
}


@app.get("/geocode")
def geocode(
    city: str = Query(..., description="City name (e.g. 'Mumbai, India' or 'Delhi')"),
) -> JSONResponse:
    """Resolve city name to latitude, longitude, and timezone offset (hours). Uses fallback list + OSM Nominatim."""
    try:
        from timezonefinder import TimezoneFinder
        from zoneinfo import ZoneInfo
        from datetime import datetime
        from urllib.parse import quote
        from urllib.request import urlopen, Request
        import json
    except ImportError as e:
        raise HTTPException(status_code=501, detail=f"Geocoding not available: {e}")

    city = (city or "").strip()
    if not city:
        raise HTTPException(status_code=400, detail="city is required")

    # Try built-in fallback first (works offline, no 502)
    key = city.lower().strip()
    # Allow "Bangalore, India" -> "bangalore"
    if "," in key:
        key = key.split(",")[0].strip()
    if key in GEOCODE_FALLBACK:
        lat, lon, tz_hours, name = GEOCODE_FALLBACK[key]
        return JSONResponse({
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "tz": round(tz_hours, 2),
            "name": name,
        })

    # Else call Nominatim (may 502 if network/SSL issue)
    url = f"https://nominatim.openstreetmap.org/search?q={quote(city)}&format=json&addressdetails=1&limit=1"
    req = Request(url, headers={"User-Agent": "LyraApp/1.0 (https://github.com/lyra)"})
    try:
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="City lookup unavailable. Try: Delhi, Mumbai, Bangalore, Chennai, Hyderabad, Pune, Kolkata.",
        )

    if not data or not isinstance(data, list) or len(data) == 0:
        raise HTTPException(status_code=404, detail=f"No location found for: {city}")

    first = data[0]
    try:
        lat = float(first["lat"])
        lon = float(first["lon"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=404, detail=f"No coordinates for: {city}")

    display_name = first.get("display_name") or city
    tf = TimezoneFinder()
    tz_name = tf.timezone_at(lng=lon, lat=lat)
    if not tz_name:
        tz_name = "UTC"
    try:
        z = ZoneInfo(tz_name)
        offset_sec = datetime.now(z).utcoffset()
        tz_hours = offset_sec.total_seconds() / 3600.0 if offset_sec else 0.0
    except Exception:
        tz_hours = 0.0

    return JSONResponse({
        "lat": round(lat, 6),
        "lon": round(lon, 6),
        "tz": round(tz_hours, 2),
        "name": display_name,
    })


@app.get("/day")
def day(
    date_str: str = Query(..., alias="date", description="YYYY-MM-DD"),
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    tz: float = Query(..., description="Timezone offset hours (e.g., 5.5 for IST)"),
    region: str = Query("NORTH_INDIA", description="NORTH_INDIA or SOUTH_INDIA"),
    anchor: str = Query(DEFAULT_ANCHOR, description="SUNRISE or NOW"),
    ayanamsa: str = Query(DEFAULT_AYANAMSA, description="Ayanamsa mode string (pass-through to PyJHora)"),
    place_name: Optional[str] = Query(None, description="Optional place name"),
) -> JSONResponse:
    parse_date(date_str)
    ensure_lat_lon(lat, lon)
    ensure_tz(tz)

    if USE_PRELOADED_STORE and _db_path:
        row = store_get_day(date_str, lat, lon, tz, _db_path)
        if row is not None:
            place_used = PRELOADED_PLACE_NAMES.get(row.get("place_id", ""))
            return JSONResponse(_day_response_from_store_row(row, lat, lon, tz, place_name, place_used=place_used))
        # No exact match: use nearest preloaded city so we avoid slow engine (jhora) path
        nearest = store_get_nearest_place(lat, lon, tz, _db_path)
        if nearest is not None:
            nlat, nlon, ntz = nearest
            row = store_get_day(date_str, nlat, nlon, ntz, _db_path)
            if row is not None:
                place_used = PRELOADED_PLACE_NAMES.get(row.get("place_id", ""))
                return JSONResponse(_day_response_from_store_row(row, lat, lon, tz, place_name, place_used=place_used))

    place = Place(lat=lat, lon=lon, tz=tz, name=place_name)
    settings = make_settings(region=region, anchor=anchor, ayanamsa=ayanamsa)

    try:
        result = compute_day(date_str, place, settings, WEIGHTS)
        return JSONResponse(dataclass_to_dict(result))
    except Exception as e:
        raise engine_error_to_http(e)


@app.get("/range")
def range_endpoint(
    start: str = Query(..., description="Start date YYYY-MM-DD"),
    end: str = Query(..., description="End date YYYY-MM-DD (inclusive)"),
    lat: float = Query(...),
    lon: float = Query(...),
    tz: float = Query(...),
    region: str = Query("NORTH_INDIA"),
    anchor: str = Query(DEFAULT_ANCHOR),
    ayanamsa: str = Query(DEFAULT_AYANAMSA),
    place_name: Optional[str] = Query(None),
) -> JSONResponse:
    d1 = parse_date(start)
    d2 = parse_date(end)
    if d2 < d1:
        raise HTTPException(status_code=400, detail="end must be >= start")

    ensure_lat_lon(lat, lon)
    ensure_tz(tz)

    if USE_PRELOADED_STORE and _db_path:
        rows = store_get_range(start, end, lat, lon, tz, _db_path)
        if rows:
            out = [_day_response_from_store_row(r, lat, lon, tz, place_name) for r in rows]
            return JSONResponse(out)
        nearest = store_get_nearest_place(lat, lon, tz, _db_path)
        if nearest is not None:
            nlat, nlon, ntz = nearest
            rows = store_get_range(start, end, nlat, nlon, ntz, _db_path)
            if rows:
                out = [_day_response_from_store_row(r, lat, lon, tz, place_name) for r in rows]
                return JSONResponse(out)

    place = Place(lat=lat, lon=lon, tz=tz, name=place_name)
    settings = make_settings(region=region, anchor=anchor, ayanamsa=ayanamsa)

    try:
        results = compute_range(start, end, place, settings, WEIGHTS)
        return JSONResponse(dataclass_to_dict(results))
    except Exception as e:
        raise engine_error_to_http(e)


@app.get("/heatmap")
def heatmap_endpoint(
    start: str = Query(..., description="Start date YYYY-MM-DD"),
    end: str = Query(..., description="End date YYYY-MM-DD (inclusive)"),
    lat: float = Query(...),
    lon: float = Query(...),
    tz: float = Query(...),
    region: str = Query("NORTH_INDIA"),
    anchor: str = Query(DEFAULT_ANCHOR),
    ayanamsa: str = Query(DEFAULT_AYANAMSA),
    place_name: Optional[str] = Query(None),
) -> JSONResponse:
    d1 = parse_date(start)
    d2 = parse_date(end)
    if d2 < d1:
        raise HTTPException(status_code=400, detail="end must be >= start")

    ensure_lat_lon(lat, lon)
    ensure_tz(tz)

    if USE_PRELOADED_STORE and _db_path:
        rows = store_get_heatmap(start, end, lat, lon, tz, _db_path)
        if rows:
            return JSONResponse(rows)
        nearest = store_get_nearest_place(lat, lon, tz, _db_path)
        if nearest is not None:
            nlat, nlon, ntz = nearest
            rows = store_get_heatmap(start, end, nlat, nlon, ntz, _db_path)
            if rows:
                return JSONResponse(rows)

    place = Place(lat=lat, lon=lon, tz=tz, name=place_name)
    settings = make_settings(region=region, anchor=anchor, ayanamsa=ayanamsa)

    try:
        results = compute_heatmap(start, end, place, settings, WEIGHTS)
        return JSONResponse(dataclass_to_dict(results))
    except Exception as e:
        raise engine_error_to_http(e)


# ------------------------------------------------------------
# Profile endpoints (birth chart + Tara Bala / personal alignment)
# ------------------------------------------------------------

@app.get("/p/day")
def day_profile(
    date_str: str = Query(..., alias="date", description="YYYY-MM-DD"),
    lat: float = Query(..., description="Current location latitude"),
    lon: float = Query(..., description="Current location longitude"),
    tz: float = Query(..., description="Current timezone offset hours"),
    birth_date: str = Query(..., description="Birth date YYYY-MM-DD"),
    birth_time: str = Query(..., description="Birth time HH:MM 24h"),
    pob_lat: float = Query(..., description="Place of birth latitude"),
    pob_lon: float = Query(..., description="Place of birth longitude"),
    pob_tz: float = Query(..., description="Place of birth timezone offset hours"),
    pob_name: Optional[str] = Query(None),
    region: str = Query("NORTH_INDIA"),
    anchor: str = Query(DEFAULT_ANCHOR),
    ayanamsa: str = Query(DEFAULT_AYANAMSA),
    place_name: Optional[str] = Query(None),
) -> JSONResponse:
    parse_date(date_str)
    parse_date(birth_date)
    ensure_lat_lon(lat, lon)
    ensure_lat_lon(pob_lat, pob_lon)
    ensure_tz(tz)
    ensure_tz(pob_tz)
    current_place = Place(lat=lat, lon=lon, tz=tz, name=place_name)
    settings = make_settings(region=region, anchor=anchor, ayanamsa=ayanamsa)
    birth = BirthDetails(
        birth_date=birth_date,
        birth_time=birth_time,
        place_of_birth=ProfilePlace(lat=pob_lat, lon=pob_lon, tz=pob_tz, name=pob_name),
    )
    key = build_cache_key(
        "profile_day",
        date=date_str,
        current_place=current_place,
        settings=settings,
        birth_date=birth_date,
        birth_time=birth_time,
        pob_lat=pob_lat,
        pob_lon=pob_lon,
        pob_tz=pob_tz,
        weights=DEFAULT_WEIGHTS_PATH,
    )
    hit = PROFILE_CACHE.get(key)
    if hit is not None:
        return JSONResponse(dataclass_to_dict(hit))

    if USE_PRELOADED_STORE and _db_path:
        row = store_get_day(date_str, lat, lon, tz, _db_path)
        if row is None:
            nearest = store_get_nearest_place(lat, lon, tz, _db_path)
            if nearest is not None:
                nlat, nlon, ntz = nearest
                row = store_get_day(date_str, nlat, nlon, ntz, _db_path)
        if row is not None:
            place_used = PRELOADED_PLACE_NAMES.get(row.get("place_id", ""))
            day_dict = _day_response_from_store_row(row, lat, lon, tz, place_name, place_used=place_used)
            overlay = profile_engine.build_profile_overlay_from_day_data(day_dict, birth, WEIGHTS)
            day_dict["profile"] = overlay
            return JSONResponse(day_dict)

    try:
        res = profile_engine.compute_day_profile(date_str, current_place, settings, WEIGHTS, birth)
        PROFILE_CACHE.set(key, res)
        return JSONResponse(dataclass_to_dict(res))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise engine_error_to_http(e)


@app.get("/p/range")
def range_profile(
    start: str = Query(..., description="Start date YYYY-MM-DD"),
    end: str = Query(..., description="End date YYYY-MM-DD (inclusive)"),
    lat: float = Query(...),
    lon: float = Query(...),
    tz: float = Query(...),
    birth_date: str = Query(...),
    birth_time: str = Query(...),
    pob_lat: float = Query(...),
    pob_lon: float = Query(...),
    pob_tz: float = Query(...),
    pob_name: Optional[str] = Query(None),
    region: str = Query("NORTH_INDIA"),
    anchor: str = Query(DEFAULT_ANCHOR),
    ayanamsa: str = Query(DEFAULT_AYANAMSA),
    place_name: Optional[str] = Query(None),
) -> JSONResponse:
    d1 = parse_date(start)
    d2 = parse_date(end)
    parse_date(birth_date)
    if d2 < d1:
        raise HTTPException(status_code=400, detail="end must be >= start")
    ensure_lat_lon(lat, lon)
    ensure_lat_lon(pob_lat, pob_lon)
    ensure_tz(tz)
    ensure_tz(pob_tz)
    current_place = Place(lat=lat, lon=lon, tz=tz, name=place_name)
    settings = make_settings(region=region, anchor=anchor, ayanamsa=ayanamsa)
    birth = BirthDetails(
        birth_date=birth_date,
        birth_time=birth_time,
        place_of_birth=ProfilePlace(lat=pob_lat, lon=pob_lon, tz=pob_tz, name=pob_name),
    )
    key = build_cache_key(
        "profile_range",
        start=start,
        end=end,
        current_place=current_place,
        settings=settings,
        birth_date=birth_date,
        birth_time=birth_time,
        pob_lat=pob_lat,
        pob_lon=pob_lon,
        pob_tz=pob_tz,
        weights=DEFAULT_WEIGHTS_PATH,
    )
    hit = PROFILE_CACHE.get(key)
    if hit is not None:
        return JSONResponse(dataclass_to_dict(hit))
    try:
        res = profile_engine.compute_range_profile(start, end, current_place, settings, WEIGHTS, birth)
        PROFILE_CACHE.set(key, res)
        return JSONResponse(dataclass_to_dict(res))
    except Exception as e:
        raise engine_error_to_http(e)
