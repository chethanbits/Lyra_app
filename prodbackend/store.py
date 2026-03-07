# store.py
"""
Lyra preloaded alignment store — SQLite backend.

Schema:
  - preloaded_alignment: (date TEXT, place_id TEXT, score INT, band TEXT,
      tithi_index INT, nakshatra_index INT, panchanga_json TEXT, summary_json TEXT,
      PRIMARY KEY (date, place_id))

Place_id format: "lat_lon_tz" rounded for consistency (e.g. "28.61_77.21_5.5").
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

# Default path relative to prodbackend
DEFAULT_DB_PATH = Path(__file__).resolve().parent / "lyra_preloaded.db"


def _place_id(lat: float, lon: float, tz: float) -> str:
    """Canonical place key for storage (rounded to 2 decimals)."""
    return f"{round(lat, 2)}_{round(lon, 2)}_{round(tz, 1)}"


def init_db(db_path: Path | str = DEFAULT_DB_PATH) -> None:
    """Create tables if they don't exist."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS preloaded_alignment (
                date TEXT NOT NULL,
                place_id TEXT NOT NULL,
                score INTEGER NOT NULL,
                band TEXT NOT NULL,
                tithi_index INTEGER NOT NULL,
                nakshatra_index INTEGER NOT NULL,
                panchanga_json TEXT,
                summary_json TEXT,
                PRIMARY KEY (date, place_id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_preloaded_date ON preloaded_alignment(date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_preloaded_place ON preloaded_alignment(place_id)")
        conn.commit()
    finally:
        conn.close()


def get_day(
    date_yyyy_mm_dd: str,
    lat: float,
    lon: float,
    tz: float,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> Optional[Dict[str, Any]]:
    """Return one day's preloaded record or None."""
    pid = _place_id(lat, lon, tz)
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute(
            "SELECT score, band, tithi_index, nakshatra_index, panchanga_json, summary_json "
            "FROM preloaded_alignment WHERE date = ? AND place_id = ?",
            (date_yyyy_mm_dd, pid),
        ).fetchone()
        if not row:
            return None
        return {
            "date": date_yyyy_mm_dd,
            "place_id": pid,
            "score": row[0],
            "band": row[1],
            "tithi_index": row[2],
            "nakshatra_index": row[3],
            "panchanga_json": json.loads(row[4]) if row[4] else None,
            "summary_json": json.loads(row[5]) if row[5] else None,
        }
    finally:
        conn.close()


def get_preloaded_place_coords(db_path: Path | str = DEFAULT_DB_PATH) -> List[tuple]:
    """Return list of (lat, lon, tz) for all preloaded place_ids (for nearest-place fallback)."""
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            "SELECT DISTINCT place_id FROM preloaded_alignment"
        ).fetchall()
        out = []
        for (pid,) in rows:
            parts = pid.split("_")
            if len(parts) == 3:
                try:
                    out.append((float(parts[0]), float(parts[1]), float(parts[2])))
                except ValueError:
                    pass
        return out
    finally:
        conn.close()


def get_nearest_preloaded_place(
    lat: float,
    lon: float,
    tz: float,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> Optional[tuple]:
    """Return (lat, lon, tz) of the nearest preloaded place, or None if DB empty."""
    coords = get_preloaded_place_coords(db_path)
    if not coords:
        return None
    best = min(coords, key=lambda c: (lat - c[0]) ** 2 + (lon - c[1]) ** 2)
    return best


def get_range(
    start_date: str,
    end_date: str,
    lat: float,
    lon: float,
    tz: float,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> List[Dict[str, Any]]:
    """Return preloaded records for date range (inclusive)."""
    pid = _place_id(lat, lon, tz)
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            "SELECT date, score, band, tithi_index, nakshatra_index, panchanga_json, summary_json "
            "FROM preloaded_alignment WHERE place_id = ? AND date >= ? AND date <= ? ORDER BY date",
            (pid, start_date, end_date),
        ).fetchall()
        return [
            {
                "date": r[0],
                "place_id": pid,
                "score": r[1],
                "band": r[2],
                "tithi_index": r[3],
                "nakshatra_index": r[4],
                "panchanga_json": json.loads(r[5]) if r[5] else None,
                "summary_json": json.loads(r[6]) if r[6] else None,
            }
            for r in rows
        ]
    finally:
        conn.close()


def get_heatmap(
    start_date: str,
    end_date: str,
    lat: float,
    lon: float,
    tz: float,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> List[Dict[str, Any]]:
    """Return lightweight heatmap rows: date, score, band, tithi_index, nakshatra_index."""
    rows = get_range(start_date, end_date, lat, lon, tz, db_path)
    return [
        {
            "date": r["date"],
            "score": r["score"],
            "band": r["band"],
            "tithi_index": r["tithi_index"],
            "nakshatra_index": r["nakshatra_index"],
        }
        for r in rows
    ]


def write_day(
    date_yyyy_mm_dd: str,
    place_id: str,
    score: int,
    band: str,
    tithi_index: int,
    nakshatra_index: int,
    panchanga_json: Optional[Dict[str, Any]] = None,
    summary_json: Optional[List[str]] = None,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> None:
    """Insert or replace one day's preloaded record."""
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            """INSERT OR REPLACE INTO preloaded_alignment
               (date, place_id, score, band, tithi_index, nakshatra_index, panchanga_json, summary_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                date_yyyy_mm_dd,
                place_id,
                score,
                band,
                tithi_index,
                nakshatra_index,
                json.dumps(panchanga_json) if panchanga_json else None,
                json.dumps(summary_json) if summary_json else None,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def place_id_from_place(lat: float, lon: float, tz: float) -> str:
    """Expose for preload script."""
    return _place_id(lat, lon, tz)
