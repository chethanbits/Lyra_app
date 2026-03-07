# preload.py
"""
Preload alignment data for 365 days × 10 cities (Delhi, Mumbai, Chennai, Bangalore, Pune, Hyderabad, Kolkata, Varanasi, Jaipur, Ahmedabad) into the SQLite store.

Run once after setting up the environment (including Swiss Ephemeris data path if needed):
  cd prodbackend
  python preload.py [--year 2026] [--db path/to/lyra_preloaded.db]

Uses engine.compute_day() and store.write_day(). Requires PyJHora + ephemeris files.
"""

from __future__ import annotations

import argparse
import os
from datetime import date, timedelta
from pathlib import Path

# Set Swiss Ephemeris path before jhora/engine are imported (jhora looks at jhora/data/ephe otherwise)
_ephe = os.environ.get("SWISSEPH_EPHE_PATH") or str(Path(__file__).resolve().parent / "ephe")
if Path(_ephe).is_dir():
    import shutil
    import sys
    import swisseph as _swe
    _swe.set_ephe_path(_ephe)
    # Jhora uses jhora/data/ephe — copy our ephe files there so jhora finds them
    for _p in sys.path:
        _jhora_ephe = Path(_p) / "jhora" / "data" / "ephe"
        if _jhora_ephe.is_dir():
            for _f in Path(_ephe).glob("*.se1"):
                _dest = _jhora_ephe / _f.name
                if not _dest.exists() or _dest.stat().st_size != _f.stat().st_size:
                    shutil.copy2(_f, _dest)
            break

# Cities: name -> (lat, lon, tz)
CITIES = {
    "Delhi": (28.6139, 77.2090, 5.5),
    "Mumbai": (19.0760, 72.8777, 5.5),
    "Chennai": (13.0827, 80.2707, 5.5),
    "Bangalore": (12.9716, 77.5946, 5.5),
    "Pune": (18.5204, 73.8567, 5.5),
    "Hyderabad": (17.3850, 78.4867, 5.5),
    "Kolkata": (22.5726, 88.3639, 5.5),
    "Varanasi": (25.3176, 82.9739, 5.5),
    "Jaipur": (26.9124, 75.7873, 5.5),
    "Ahmedabad": (23.0225, 72.5714, 5.5),
}


def _panchanga_to_json(panchanga) -> dict:
    """Convert PanchangaSnapshot to JSON-serializable dict."""
    from dataclasses import asdict, is_dataclass
    def _to_dict(obj):
        if obj is None or isinstance(obj, (str, int, float, bool)):
            return obj
        if hasattr(obj, "value"):  # Enum
            return obj.value
        if is_dataclass(obj) and not isinstance(obj, type):
            return {k: _to_dict(v) for k, v in asdict(obj).items()}
        if isinstance(obj, dict):
            return {k: _to_dict(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_to_dict(x) for x in obj]
        return str(obj)
    return _to_dict(asdict(panchanga))


def main() -> None:
    parser = argparse.ArgumentParser(description="Preload Lyra alignment data (365 days × 10 cities)")
    parser.add_argument("--year", type=int, default=2026, help="Year to generate")
    parser.add_argument("--db", type=str, default=None, help="SQLite DB path (default: prodbackend/lyra_preloaded.db)")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    weights_path = root / "weights_balanced.yaml"
    db_path = Path(args.db) if args.db else root / "lyra_preloaded.db"

    from engine import (
        Place,
        EngineSettings,
        RegionMode,
        AnchorMode,
        load_weights_config,
        compute_day,
    )
    from store import init_db, write_day, place_id_from_place

    init_db(db_path)
    weights = load_weights_config(weights_path)
    settings = EngineSettings(region_mode=RegionMode.NORTH_INDIA, anchor=AnchorMode.SUNRISE)

    start = date(args.year, 1, 1)
    total = 0
    for city_name, (lat, lon, tz) in CITIES.items():
        place = Place(lat=lat, lon=lon, tz=tz, name=city_name)
        pid = place_id_from_place(lat, lon, tz)
        print(f"Preloading {city_name} ({pid}) ...")
        for i in range(365):
            d = start + timedelta(days=i)
            date_str = d.strftime("%Y-%m-%d")
            try:
                result = compute_day(date_str, place, settings, weights)
            except Exception as e:
                print(f"  ERROR {date_str}: {e}")
                continue
            panchanga_dict = _panchanga_to_json(result.panchanga)
            write_day(
                date_yyyy_mm_dd=date_str,
                place_id=pid,
                score=result.score.alignment_score,
                band=result.score.band.value,
                tithi_index=result.panchanga.tithi.index,
                nakshatra_index=result.panchanga.nakshatra.index,
                panchanga_json=panchanga_dict,
                summary_json=result.score.summary,
                db_path=db_path,
            )
            total += 1
        print(f"  -> {365} days written.")
    print(f"Done. Total rows: {total}. DB: {db_path}")


if __name__ == "__main__":
    main()
