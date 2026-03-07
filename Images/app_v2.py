# app_v2.py
"""
Lyra API v2 (Guest + Profile)

DO NOT replace your existing app.py if you want to keep old behavior untouched.
Instead, run this as a new server entry point:

  uvicorn app_v2:app --reload --port 8000

GUEST MODE endpoints:
  GET /day
  GET /range
  GET /heatmap

PROFILE MODE endpoints (registered user):
  GET /p/day
  GET /p/range

Profile endpoints require birth inputs:
  birth_date=YYYY-MM-DD
  birth_time=HH:MM
  pob_lat, pob_lon, pob_tz
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse

import engine_guest as guest
import engine_profile as profile
from profiles import BirthDetails, Place as ProfilePlace
from cache import TTLCache, build_cache_key


WEIGHTS_PATH = os.environ.get("LYRA_WEIGHTS_PATH", "weights_balanced.yaml")
DEFAULT_REGION = os.environ.get("LYRA_REGION", "NORTH_INDIA")
DEFAULT_ANCHOR = os.environ.get("LYRA_ANCHOR", "SUNRISE")
DEFAULT_AYANAMSA = os.environ.get("LYRA_AYANAMSA", "LAHIRI")

WEIGHTS = guest.load_weights_config(WEIGHTS_PATH)

CACHE = TTLCache(max_items=20000, ttl_seconds=24 * 3600)

app = FastAPI(title="Lyra Engine API v2", version="2.0.0")


def _to_jsonable(x: Any) -> Any:
    if x is None:
        return None
    if hasattr(x, "value"):
        try:
            return x.value
        except Exception:
            pass
    if isinstance(x, (str, int, float, bool)):
        return x
    if isinstance(x, dict):
        return {str(k): _to_jsonable(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_to_jsonable(v) for v in x]
    if hasattr(x, "__dict__"):
        return _to_jsonable(x.__dict__)
    return str(x)


def _settings(region: str, anchor: str, ayanamsa: str) -> guest.EngineSettings:
    try:
        r = guest.RegionMode(region.upper())
    except Exception:
        raise HTTPException(400, "region must be NORTH_INDIA or SOUTH_INDIA")
    try:
        a = guest.AnchorMode(anchor.upper())
    except Exception:
        raise HTTPException(400, "anchor must be SUNRISE or NOW")
    return guest.EngineSettings(region_mode=r, anchor=a, ayanamsa_mode=ayanamsa)


def _engine_error(e: Exception) -> HTTPException:
    if isinstance(e, guest.EngineError):
        return HTTPException(400, {"code": e.code.value, "message": e.message, "details": e.details})
    return HTTPException(500, str(e))


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "weights": WEIGHTS_PATH, "mode": "guest+profile"}


# -----------------------------
# Guest endpoints (unchanged behavior)
# -----------------------------

@app.get("/day")
def day(
    date: str = Query(..., description="YYYY-MM-DD"),
    lat: float = Query(...),
    lon: float = Query(...),
    tz: float = Query(..., description="timezone offset hours"),
    region: str = Query(DEFAULT_REGION),
    anchor: str = Query(DEFAULT_ANCHOR),
    ayanamsa: str = Query(DEFAULT_AYANAMSA),
    place_name: Optional[str] = Query(None),
) -> JSONResponse:
    place = guest.Place(lat=lat, lon=lon, tz=tz, name=place_name)
    settings = _settings(region, anchor, ayanamsa)

    key = build_cache_key("guest_day", date=date, place=place, settings=settings, weights=WEIGHTS_PATH)
    hit = CACHE.get(key)
    if hit is not None:
        return JSONResponse(_to_jsonable(hit))

    try:
        res = guest.compute_day(date, place, settings, WEIGHTS)
        CACHE.set(key, res)
        return JSONResponse(_to_jsonable(res))
    except Exception as e:
        raise _engine_error(e)


@app.get("/range")
def range_(
    start: str = Query(...),
    end: str = Query(...),
    lat: float = Query(...),
    lon: float = Query(...),
    tz: float = Query(...),
    region: str = Query(DEFAULT_REGION),
    anchor: str = Query(DEFAULT_ANCHOR),
    ayanamsa: str = Query(DEFAULT_AYANAMSA),
    place_name: Optional[str] = Query(None),
) -> JSONResponse:
    place = guest.Place(lat=lat, lon=lon, tz=tz, name=place_name)
    settings = _settings(region, anchor, ayanamsa)

    key = build_cache_key("guest_range", start=start, end=end, place=place, settings=settings, weights=WEIGHTS_PATH)
    hit = CACHE.get(key)
    if hit is not None:
        return JSONResponse(_to_jsonable(hit))

    try:
        res = guest.compute_range(start, end, place, settings, WEIGHTS)
        CACHE.set(key, res)
        return JSONResponse(_to_jsonable(res))
    except Exception as e:
        raise _engine_error(e)


@app.get("/heatmap")
def heatmap(
    start: str = Query(...),
    end: str = Query(...),
    lat: float = Query(...),
    lon: float = Query(...),
    tz: float = Query(...),
    region: str = Query(DEFAULT_REGION),
    anchor: str = Query(DEFAULT_ANCHOR),
    ayanamsa: str = Query(DEFAULT_AYANAMSA),
    place_name: Optional[str] = Query(None),
) -> JSONResponse:
    place = guest.Place(lat=lat, lon=lon, tz=tz, name=place_name)
    settings = _settings(region, anchor, ayanamsa)

    key = build_cache_key("guest_heatmap", start=start, end=end, place=place, settings=settings, weights=WEIGHTS_PATH)
    hit = CACHE.get(key)
    if hit is not None:
        return JSONResponse(_to_jsonable(hit))

    try:
        res = guest.compute_heatmap(start, end, place, settings, WEIGHTS)
        CACHE.set(key, res)
        return JSONResponse(_to_jsonable(res))
    except Exception as e:
        raise _engine_error(e)


# -----------------------------
# Profile endpoints (NEW)
# -----------------------------

@app.get("/p/day")
def day_profile(
    date: str = Query(..., description="YYYY-MM-DD"),
    lat: float = Query(..., description="Current location latitude"),
    lon: float = Query(..., description="Current location longitude"),
    tz: float = Query(..., description="Current timezone offset hours"),

    birth_date: str = Query(..., description="YYYY-MM-DD"),
    birth_time: str = Query(..., description="HH:MM 24h"),
    pob_lat: float = Query(..., description="Place of birth latitude"),
    pob_lon: float = Query(..., description="Place of birth longitude"),
    pob_tz: float = Query(..., description="Place of birth timezone offset hours"),
    pob_name: Optional[str] = Query(None),

    region: str = Query(DEFAULT_REGION),
    anchor: str = Query(DEFAULT_ANCHOR),
    ayanamsa: str = Query(DEFAULT_AYANAMSA),
    place_name: Optional[str] = Query(None),
) -> JSONResponse:
    """
    Registered-user endpoint: returns guest facts + guest score + ProfileOverlay:
      - 4A Nakshatra Personality
      - 2A Tara Bala
      - 1A/1B Personal Alignment Score (guest + tara points)
      - 3A Muhurta windows are already in PanchangaSnapshot (facts)
    """
    current_place = guest.Place(lat=lat, lon=lon, tz=tz, name=place_name)
    settings = _settings(region, anchor, ayanamsa)

    birth = BirthDetails(
        birth_date=birth_date,
        birth_time=birth_time,
        place_of_birth=ProfilePlace(lat=pob_lat, lon=pob_lon, tz=pob_tz, name=pob_name),
    )

    key = build_cache_key(
        "profile_day",
        date=date,
        current_place=current_place,
        settings=settings,
        birth_date=birth_date,
        birth_time=birth_time,
        pob_lat=pob_lat,
        pob_lon=pob_lon,
        pob_tz=pob_tz,
        weights=WEIGHTS_PATH,
    )
    hit = CACHE.get(key)
    if hit is not None:
        return JSONResponse(_to_jsonable(hit))

    try:
        res = profile.compute_day_profile(date, current_place, settings, WEIGHTS, birth)
        CACHE.set(key, res)
        return JSONResponse(_to_jsonable(res))
    except Exception as e:
        raise _engine_error(e)


@app.get("/p/range")
def range_profile(
    start: str = Query(...),
    end: str = Query(...),

    lat: float = Query(...),
    lon: float = Query(...),
    tz: float = Query(...),

    birth_date: str = Query(...),
    birth_time: str = Query(...),
    pob_lat: float = Query(...),
    pob_lon: float = Query(...),
    pob_tz: float = Query(...),
    pob_name: Optional[str] = Query(None),

    region: str = Query(DEFAULT_REGION),
    anchor: str = Query(DEFAULT_ANCHOR),
    ayanamsa: str = Query(DEFAULT_AYANAMSA),
    place_name: Optional[str] = Query(None),
) -> JSONResponse:
    current_place = guest.Place(lat=lat, lon=lon, tz=tz, name=place_name)
    settings = _settings(region, anchor, ayanamsa)

    birth = BirthDetails(
        birth_date=birth_date,
        birth_time=birth_time,
        place_of_birth=ProfilePlace(lat=pob_lat, lon=pob_lon, tz=pob_tz, name=pob_name),
    )

    key = build_cache_key(
        "profile_range",
        start=start, end=end,
        current_place=current_place, settings=settings,
        birth_date=birth_date, birth_time=birth_time,
        pob_lat=pob_lat, pob_lon=pob_lon, pob_tz=pob_tz,
        weights=WEIGHTS_PATH,
    )
    hit = CACHE.get(key)
    if hit is not None:
        return JSONResponse(_to_jsonable(hit))

    try:
        res = profile.compute_range_profile(start, end, current_place, settings, WEIGHTS, birth)
        CACHE.set(key, res)
        return JSONResponse(_to_jsonable(res))
    except Exception as e:
        raise _engine_error(e)