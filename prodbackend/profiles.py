# profiles.py
"""
Lyra Profile — birth details and place of birth for registered users.
Used by engine_profile and app_v2 profile endpoints.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class Place:
    """Place of birth (or any location) for profile calculations."""
    lat: float
    lon: float
    tz: float
    name: Optional[str] = None


@dataclass(frozen=True)
class BirthDetails:
    birth_date: str   # YYYY-MM-DD
    birth_time: str   # HH:MM (24h)
    place_of_birth: Place

    def to_local_datetime(self) -> datetime:
        """Return datetime at birth place in local time (for JD / nakshatra at birth)."""
        parts = self.birth_date.strip().split("-")
        if len(parts) != 3:
            raise ValueError(f"Invalid birth_date: {self.birth_date}. Use YYYY-MM-DD.")
        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        time_parts = self.birth_time.strip().split(":")
        hour = int(time_parts[0]) if len(time_parts) >= 1 else 0
        minute = int(time_parts[1]) if len(time_parts) >= 2 else 0
        second = int(time_parts[2]) if len(time_parts) >= 3 else 0
        return datetime(year, month, day, hour, minute, second)
