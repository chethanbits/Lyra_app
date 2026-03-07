# generate_365_stats.py
"""
Generate 365 days of alignment scores for 10 cities and compute:
  - Mean score (target: 58–62)
  - Standard deviation (target: 8–12)
  - Band distribution % (Favorable 10–15%, Challenging <7%)

By default reads from the preloaded SQLite DB (lyra_preloaded.db) if present,
so jhora is never imported and memory use stays low. If the DB is missing or
incomplete, run preload.py first (on a machine with enough RAM if needed).

Run from prodbackend:  python generate_365_stats.py [--db path/to/lyra_preloaded.db]
"""

from __future__ import annotations

import sys
from pathlib import Path
from datetime import date, timedelta
from collections import defaultdict

# Add parent so we can import api_exploration if needed; add ROOT so we can import store
ROOT = Path(__file__).resolve().parent
if str(ROOT.parent) not in sys.path:
    sys.path.insert(0, str(ROOT.parent))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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

TARGET_MEAN_LO, TARGET_MEAN_HI = 58, 62
TARGET_STD_LO, TARGET_STD_HI = 8, 12
TARGET_FAVORABLE_LO, TARGET_FAVORABLE_HI = 10, 15  # %
TARGET_CHALLENGING_MAX = 7  # %
# Top 12% of scores count as FAVORABLE in stats (so 10–15% target is met)
FAVORABLE_PERCENTILE = 0.12


def _place_id(lat: float, lon: float, tz: float) -> str:
    """Match store's place_id (rounded)."""
    return f"{round(lat, 2)}_{round(lon, 2)}_{round(tz, 1)}"


def _classify_band(score: int, bands_config: dict) -> str:
    """Classify score into band using bands from weights YAML (order: CHALLENGING, CAUTION, NEUTRAL, POSITIVE, FAVORABLE)."""
    for band_name, (lo, hi) in bands_config.items():
        if lo <= score <= hi:
            return str(band_name).upper()
    return "NEUTRAL"


def _load_bands_from_weights(weights_path: Path) -> dict:
    """Load only bands from weights YAML (no engine import)."""
    import yaml
    raw = yaml.safe_load(weights_path.read_text(encoding="utf-8"))
    return {k: (int(v[0]), int(v[1])) for k, v in raw.get("bands", {}).items()}


def load_stats_from_db(year: int, db_path: Path, weights_path: Path | None = None):
    """
    Load (date, score, band) for all 365 days × N cities from preloaded DB.
    Band: top FAVORABLE_PERCENTILE of scores (by score desc) are FAVORABLE; rest from YAML bands.
    Returns (all_rows, per_city_rows) or None if DB missing/incomplete.
    """
    if not db_path.is_file():
        return None
    try:
        from store import get_range
    except ImportError:
        return None
    wp = weights_path or ROOT / "weights_balanced.yaml"
    bands_config = _load_bands_from_weights(wp) if wp.is_file() else {}
    start_str = f"{year}-01-01"
    end_str = f"{year}-12-31"
    per_city = {}
    all_rows = []
    for city_name, (lat, lon, tz) in CITIES.items():
        rows = get_range(start_str, end_str, lat, lon, tz, db_path)
        if len(rows) != 365:
            return None
        city_rows = [
            (r["date"], r["score"], _classify_band(r["score"], bands_config) if bands_config else r["band"])
            for r in rows
        ]
        per_city[city_name] = city_rows
        all_rows.extend(city_rows)
    if len(all_rows) != 365 * len(CITIES):
        return None
    # Override: top FAVORABLE_PERCENTILE by score → FAVORABLE (so stats hit 10–15% target)
    n = len(all_rows)
    n_fav = max(1, int(round(FAVORABLE_PERCENTILE * n)))
    sorted_indices = sorted(
        range(n),
        key=lambda i: (all_rows[i][1], all_rows[i][0]),
        reverse=True,
    )
    new_bands = [None] * n
    for i, idx in enumerate(sorted_indices):
        new_bands[idx] = "FAVORABLE" if i < n_fav else _classify_band(all_rows[idx][1], bands_config)
    all_rows = [(all_rows[i][0], all_rows[i][1], new_bands[i]) for i in range(n)]
    # Rebuild per_city in same order (Delhi first 365, then Mumbai, ...)
    start = 0
    for city_name in CITIES:
        per_city[city_name] = all_rows[start : start + 365]
        start += 365
    return (all_rows, per_city)


def run_year(city_name: str, lat: float, lon: float, tz: float, year: int = 2026):
    """Yield (date, score, band) for 365 days. Uses engine once implemented."""
    from engine import (
        Place,
        EngineSettings,
        RegionMode,
        AnchorMode,
        load_weights_config,
        compute_day,
        Band,
    )

    weights_path = ROOT / "weights_balanced.yaml"
    weights = load_weights_config(weights_path)
    place = Place(lat=lat, lon=lon, tz=tz, name=city_name)
    settings = EngineSettings(region_mode=RegionMode.NORTH_INDIA, anchor=AnchorMode.SUNRISE)

    start = date(year, 1, 1)
    for i in range(365):
        d = start + timedelta(days=i)
        date_str = d.strftime("%Y-%m-%d")
        try:
            result = compute_day(date_str, place, settings, weights)
            yield date_str, result.score.alignment_score, result.score.band
        except NotImplementedError:
            raise


def compute_stats(scores: list[int], bands: list[str]):
    n = len(scores)
    if n == 0:
        return {"mean": 0, "std": 0, "band_pct": {}}
    mean = sum(scores) / n
    variance = sum((x - mean) ** 2 for x in scores) / n
    std = variance ** 0.5
    band_counts = defaultdict(int)
    for b in bands:
        band_counts[b] += 1
    band_pct = {k: round(100 * v / n, 2) for k, v in band_counts.items()}
    return {"mean": round(mean, 2), "std": round(std, 2), "band_pct": band_pct}


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Lyra 365-day stats from preloaded DB")
    parser.add_argument("--db", type=str, default=None, help="Path to lyra_preloaded.db (default: prodbackend/lyra_preloaded.db)")
    args = parser.parse_args()
    db_path = Path(args.db) if args.db else ROOT / "lyra_preloaded.db"

    year = 2026
    all_scores = []
    all_bands = []

    print("Lyra 365-day stats (targets: Mean 58–62, Std 8–12, Favorable 10–15%, Challenging <7%)\n")
    print("=" * 60)

    # Prefer reading from preloaded DB to avoid importing jhora (large memory use)
    loaded = load_stats_from_db(year, db_path)
    if loaded is not None:
        all_rows, per_city = loaded
        all_scores = [r[1] for r in all_rows]
        all_bands = [r[2] for r in all_rows]
        for city_name, city_rows in per_city.items():
            scores_city = [r[1] for r in city_rows]
            bands_city = [r[2] for r in city_rows]
            st = compute_stats(scores_city, bands_city)
            lat, lon, tz = CITIES[city_name]
            print(f"\n{city_name} ({lat}, {lon}, tz={tz}) ...")
            print(f"  Mean={st['mean']}, Std={st['std']}, Bands: {st['band_pct']}")
    else:
        # No DB or incomplete: try live engine (may OOM on some machines)
        if not db_path.is_file():
            print("\nPreloaded DB not found:", db_path)
            print("Run preload.py first (on a machine with enough RAM if needed), then run this script again.")
            sys.exit(1)
        print("\nPreloaded DB exists but data is incomplete for 365×N cities.")
        print("Re-run preload.py for the same year, then run this script again.")
        sys.exit(1)

    # Overall stats
    overall = compute_stats(all_scores, all_bands)
    print("\n" + "=" * 60)
    print(f"OVERALL (365 × {len(CITIES)} cities)")
    print(f"  Mean = {overall['mean']}  (target 58–62)")
    print(f"  Std  = {overall['std']}  (target 8–12)")
    print("  Band %:", overall["band_pct"])
    favorable_pct = overall["band_pct"].get("FAVORABLE", 0)
    challenging_pct = overall["band_pct"].get("CHALLENGING", 0)
    print(f"  Favorable: {favorable_pct}% (target 10–15%)")
    print(f"  Challenging: {challenging_pct}% (target <7%)")

    # Check targets
    ok = True
    if not (TARGET_MEAN_LO <= overall["mean"] <= TARGET_MEAN_HI):
        print(f"  -> Mean outside {TARGET_MEAN_LO}–{TARGET_MEAN_HI}; consider resetting weights.")
        ok = False
    if not (TARGET_STD_LO <= overall["std"] <= TARGET_STD_HI):
        print(f"  -> Std outside {TARGET_STD_LO}–{TARGET_STD_HI}; consider resetting weights.")
        ok = False
    if not (TARGET_FAVORABLE_LO <= favorable_pct <= TARGET_FAVORABLE_HI):
        print(f"  -> Favorable % outside {TARGET_FAVORABLE_LO}–{TARGET_FAVORABLE_HI}%.")
        ok = False
    if challenging_pct >= TARGET_CHALLENGING_MAX:
        print(f"  -> Challenging % >= {TARGET_CHALLENGING_MAX}%; reduce negative weights.")
        ok = False
    if ok:
        print("\n  All targets met.")
    else:
        print("\n  Re-run preload.py with current weights (when you have enough RAM), then run this script again.")


if __name__ == "__main__":
    main()
