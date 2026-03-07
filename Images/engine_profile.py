# engine_profile.py
"""
Lyra Profile Engine (Registered user mode)

USE THIS FOR:
- Registered users who provide DOB/TOB/POB
- V1 personalized features selected by you:
  1A Home Alignment Card (personal)
  1B Daily Alignment Section (personal)
  2A Tara Bala Tracker
  3A Muhurta suggestions (facts + avoid windows already in Panchang)
  4A Nakshatra Personality (birth nakshatra)

IMPORTANT:
- Guest mode remains in engine_guest.py
- This module *wraps guest results* and adds profile overlays.
- UI should call /p/day (or /profile/day) endpoints for registered users.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from profiles import BirthDetails, Place as ProfilePlace
import engine_guest as guest


# -----------------------------
# Profile-specific models
# -----------------------------

@dataclass(frozen=True)
class TaraBalaResult:
    birth_nakshatra: str
    birth_nakshatra_index: int
    todays_nakshatra: str
    todays_nakshatra_index: int
    tara_number: int              # 1..9
    tara_name: str                # Janma/Sampat/...
    tara_category: str            # "FAVORABLE" or "UNFAVORABLE"


@dataclass(frozen=True)
class NakshatraPersonality:
    nakshatra: str
    nakshatra_index: int
    ruling_planet: Optional[str] = None
    symbol: Optional[str] = None
    deity: Optional[str] = None
    keywords: Optional[List[str]] = None


@dataclass(frozen=True)
class ProfileOverlay:
    # 4A
    personality: NakshatraPersonality
    # 2A
    tara_bala: TaraBalaResult
    # 1A/1B personal alignment additions
    personal_alignment_score: int
    personal_band: guest.Band
    personal_breakdown: List[guest.ScoreBreakdownItem]


@dataclass(frozen=True)
class ProfileDayResult:
    """
    Guest facts + guest score (still returned)
    + profile overlay
    """
    panchanga: guest.PanchangaSnapshot
    score: guest.ScoreResult                 # guest score
    summary_lines: List[str]                 # guest deterministic summary (UI may ignore)
    profile: ProfileOverlay                  # NEW


# -----------------------------
# Public APIs (Profile Mode)
# -----------------------------

def compute_day_profile(
    date_str: str,
    current_place: guest.Place,
    settings: guest.EngineSettings,
    weights: guest.WeightsConfig,
    birth: BirthDetails,
) -> ProfileDayResult:
    """
    Registered-user day result:
    - gets guest day output
    - computes birth nakshatra (from birth datetime + POB)
    - computes Tara Bala (2A)
    - computes personal alignment score (1A/1B) as guest score + tara contribution
    - returns Nakshatra Personality (4A) as structured facts
    """
    day = guest.compute_day(date_str, current_place, settings, weights)

    birth_nak_name, birth_nak_idx = _compute_birth_nakshatra(birth, settings)
    todays_nak_name, todays_nak_idx = _todays_nakshatra(day.panchanga)

    tara = _compute_tara_bala(
        birth_nakshatra=birth_nak_name,
        birth_idx=birth_nak_idx,
        today_nakshatra=todays_nak_name,
        today_idx=todays_nak_idx,
    )

    personality = _get_nakshatra_personality(birth_nak_name, birth_nak_idx)

    # Personal alignment: guest score + tara contribution (simple and stable for V1)
    tara_points = 4 if tara.tara_category == "FAVORABLE" else -4

    personal_raw = day.score.alignment_score + tara_points
    personal_score = max(0, min(100, int(personal_raw)))
    personal_band = guest.classify_band(personal_score, weights.bands)

    personal_breakdown = list(day.score.breakdown) + [
        guest.ScoreBreakdownItem("TARA_BALA", tara_points, f"{tara.tara_name} Tara"),
    ]

    overlay = ProfileOverlay(
        personality=personality,
        tara_bala=tara,
        personal_alignment_score=personal_score,
        personal_band=personal_band,
        personal_breakdown=personal_breakdown,
    )

    return ProfileDayResult(
        panchanga=day.panchanga,
        score=day.score,
        summary_lines=day.summary_lines,
        profile=overlay,
    )


def compute_range_profile(
    start: str,
    end: str,
    current_place: guest.Place,
    settings: guest.EngineSettings,
    weights: guest.WeightsConfig,
    birth: BirthDetails,
) -> List[ProfileDayResult]:
    d1 = datetime.strptime(start, "%Y-%m-%d").date()
    d2 = datetime.strptime(end, "%Y-%m-%d").date()
    if d2 < d1:
        raise guest.EngineError(guest.EngineErrorCode.INVALID_INPUT, "end must be >= start")

    out: List[ProfileDayResult] = []
    cur = d1
    while cur <= d2:
        out.append(compute_day_profile(cur.isoformat(), current_place, settings, weights, birth))
        cur += timedelta(days=1)
    return out


# -----------------------------
# Tara Bala / Birth Nakshatra
# -----------------------------

def _compute_birth_nakshatra(birth: BirthDetails, settings: guest.EngineSettings) -> Tuple[str, int]:
    """
    Computes Janma Nakshatra at birth time/location using PyJHora drik.nakshatra()

    This returns:
      (nakshatra_name, nakshatra_index 1..27)

    If your PyJHora version returns different tuple shapes, adjust _parse_nakshatra_result().
    """
    try:
        from jhora.panchanga import drik  # type: ignore
        from jhora import utils  # type: ignore
    except Exception as e:
        raise guest.EngineError(guest.EngineErrorCode.PYJHORA_ERROR, f"Failed to import PyJHora: {e}")

    # set ayanamsa if supported
    try:
        if hasattr(drik, "set_ayanamsa_mode"):
            drik.set_ayanamsa_mode(settings.ayanamsa_mode)
    except Exception:
        pass

    pob = birth.place_of_birth
    pj_place = drik.Place(pob.name or "BirthPlace", pob.lat, pob.lon, pob.tz)

    dt_local = birth.to_local_datetime()
    # JD base for birth date
    try:
        jd0 = utils.gregorian_to_jd(drik.Date(dt_local.year, dt_local.month, dt_local.day))
    except Exception:
        jd0 = utils.gregorian_to_jd((dt_local.year, dt_local.month, dt_local.day))

    frac = (dt_local.hour * 3600 + dt_local.minute * 60) / 86400.0
    jd_birth = jd0 + frac

    res = drik.nakshatra(jd_birth, pj_place)
    return _parse_nakshatra_result(res)


def _parse_nakshatra_result(res: Any) -> Tuple[str, int]:
    """
    Expected common format: (idx, name, end_time_str, end_jd, ...)
    But this function is defensive.
    """
    if isinstance(res, (list, tuple)):
        idx = None
        name = None
        if len(res) >= 1 and isinstance(res[0], int):
            idx = int(res[0])
        if len(res) >= 2:
            name = str(res[1])
        if idx is None:
            # try to find an int
            for x in res:
                if isinstance(x, int):
                    idx = int(x)
                    break
        if name is None:
            # find first non-time string
            for x in res:
                if isinstance(x, str) and x.strip() and ":" not in x:
                    name = x.strip()
                    break
        if idx is None or name is None:
            raise guest.EngineError(guest.EngineErrorCode.PYJHORA_ERROR, f"Unrecognized nakshatra format: {res}")
        return (name, idx)

    raise guest.EngineError(guest.EngineErrorCode.PYJHORA_ERROR, f"Unrecognized nakshatra return: {res}")


def _todays_nakshatra(p: guest.PanchangaSnapshot) -> Tuple[str, int]:
    if not (p.nakshatra and p.nakshatra.name and p.nakshatra.index):
        raise guest.EngineError(guest.EngineErrorCode.INVALID_INPUT, "Missing today's nakshatra in Panchang")
    return (p.nakshatra.name, int(p.nakshatra.index))


def _compute_tara_bala(
    *,
    birth_nakshatra: str,
    birth_idx: int,
    today_nakshatra: str,
    today_idx: int
) -> TaraBalaResult:
    """
    Tara number = ((today_idx - birth_idx) mod 27) + 1
    Map 1..9 repeating:
      1 Janma, 2 Sampat, 3 Vipat, 4 Kshema, 5 Pratyak,
      6 Sadhana, 7 Naidhana, 8 Mitra, 9 Parama Mitra
    """
    delta = (today_idx - birth_idx) % 27
    tara_number = (delta % 9) + 1

    tara_names = {
        1: "Janma",
        2: "Sampat",
        3: "Vipat",
        4: "Kshema",
        5: "Pratyak",
        6: "Sadhana",
        7: "Naidhana",
        8: "Mitra",
        9: "Parama Mitra",
    }
    tara_name = tara_names[tara_number]

    favorable = {2, 4, 6, 8, 9}
    category = "FAVORABLE" if tara_number in favorable else "UNFAVORABLE"

    return TaraBalaResult(
        birth_nakshatra=birth_nakshatra,
        birth_nakshatra_index=birth_idx,
        todays_nakshatra=today_nakshatra,
        todays_nakshatra_index=today_idx,
        tara_number=tara_number,
        tara_name=tara_name,
        tara_category=category,
    )


# -----------------------------
# Nakshatra Personality (V1 minimal facts)
# -----------------------------

def _get_nakshatra_personality(nak_name: str, nak_idx: int) -> NakshatraPersonality:
    """
    V1: keep this simple + factual.
    You can later expand into a full reference table without changing UI contracts.
    """
    # Minimal starter table for common fields (extend freely)
    # If nakshatra name spellings vary in PyJHora, standardize in UI layer or add synonyms here.
    table: Dict[str, Dict[str, Any]] = {
        "Ashwini": {"ruling_planet": "Ketu", "symbol": "Horse head", "deity": "Ashvins", "keywords": ["speed", "healing", "beginnings"]},
        "Rohini": {"ruling_planet": "Moon", "symbol": "Chariot", "deity": "Brahma", "keywords": ["growth", "beauty", "creation"]},
        "Jyeshtha": {"ruling_planet": "Mercury", "symbol": "Earring / Umbrella", "deity": "Indra", "keywords": ["seniority", "protection", "leadership"]},
        # Add remaining nakshatras as needed
    }
    info = table.get(nak_name, {})
    return NakshatraPersonality(
        nakshatra=nak_name,
        nakshatra_index=nak_idx,
        ruling_planet=info.get("ruling_planet"),
        symbol=info.get("symbol"),
        deity=info.get("deity"),
        keywords=info.get("keywords"),
    )