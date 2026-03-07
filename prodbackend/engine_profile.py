# engine_profile.py
"""
Lyra Profile Engine (Registered user mode).
Wraps guest results and adds profile overlays: Tara Bala, Nakshatra Personality, personal alignment.
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
    tara_number: int
    tara_name: str
    tara_category: str


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
    personality: NakshatraPersonality
    tara_bala: TaraBalaResult
    personal_alignment_score: int
    personal_band: guest.Band
    personal_breakdown: List[guest.ScoreBreakdownItem]


@dataclass(frozen=True)
class ProfileDayResult:
    panchanga: guest.PanchangaSnapshot
    score: guest.ScoreResult
    summary_lines: List[str]
    profile: ProfileOverlay


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
    day = guest.compute_day(date_str, current_place, settings, weights)
    todays_nak_name, todays_nak_idx = _todays_nakshatra(day.panchanga)
    try:
        birth_nak_name, birth_nak_idx = _compute_birth_nakshatra(birth, settings)
    except Exception:
        birth_nak_name, birth_nak_idx = todays_nak_name, todays_nak_idx
    tara = _compute_tara_bala(
        birth_nakshatra=birth_nak_name,
        birth_idx=birth_nak_idx,
        today_nakshatra=todays_nak_name,
        today_idx=todays_nak_idx,
    )
    personality = _get_nakshatra_personality(birth_nak_name, birth_nak_idx)
    tara_points = 4 if tara.tara_category == "FAVORABLE" else -4
    personal_raw = day.score.alignment_score + tara_points
    personal_score = max(0, min(100, int(personal_raw)))
    personal_band = guest.classify_band(personal_score, weights)
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
    summary_lines = getattr(day, "summary_lines", None) or (list(day.score.summary) if getattr(day.score, "summary", None) else [])
    return ProfileDayResult(
        panchanga=day.panchanga,
        score=day.score,
        summary_lines=summary_lines,
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


def build_profile_overlay_from_day_data(
    day_data: Dict[str, Any],
    birth: BirthDetails,
    weights: guest.WeightsConfig,
) -> Dict[str, Any]:
    """
    Build profile overlay from precomputed day data (e.g. from store).
    Uses today's nakshatra as birth nakshatra to avoid importing jhora (which can OOM).
    Returns a JSON-serializable dict for the "profile" key.
    """
    panchanga = day_data.get("panchanga") or {}
    score_data = day_data.get("score") or {}
    nak = panchanga.get("nakshatra") or {}
    todays_nak_name = nak.get("name") or "Ashwini"
    todays_nak_idx = int(nak.get("index", 1))
    birth_nak_name, birth_nak_idx = todays_nak_name, todays_nak_idx
    tara = _compute_tara_bala(
        birth_nakshatra=birth_nak_name,
        birth_idx=birth_nak_idx,
        today_nakshatra=todays_nak_name,
        today_idx=todays_nak_idx,
    )
    personality = _get_nakshatra_personality(birth_nak_name, birth_nak_idx)
    tara_points = 4 if tara.tara_category == "FAVORABLE" else -4
    base_score = int(score_data.get("alignment_score", 50))
    personal_raw = base_score + tara_points
    personal_score = max(0, min(100, int(personal_raw)))
    personal_band = guest.classify_band(personal_score, weights)
    breakdown_list = list(score_data.get("breakdown") or [])
    if isinstance(breakdown_list, list):
        personal_breakdown = [
            {"factor": b.get("factor", ""), "value": b.get("value", 0), "label": b.get("label", "")}
            for b in breakdown_list
        ]
    else:
        personal_breakdown = []
    personal_breakdown.append({"factor": "TARA_BALA", "value": tara_points, "label": f"{tara.tara_name} Tara"})
    band_value = personal_band.value if hasattr(personal_band, "value") else str(personal_band)
    return {
        "personality": {
            "nakshatra": personality.nakshatra,
            "nakshatra_index": personality.nakshatra_index,
            "ruling_planet": personality.ruling_planet,
            "symbol": personality.symbol,
            "deity": personality.deity,
            "keywords": personality.keywords,
        },
        "tara_bala": {
            "birth_nakshatra": tara.birth_nakshatra,
            "birth_nakshatra_index": tara.birth_nakshatra_index,
            "todays_nakshatra": tara.todays_nakshatra,
            "todays_nakshatra_index": tara.todays_nakshatra_index,
            "tara_number": tara.tara_number,
            "tara_name": tara.tara_name,
            "tara_category": tara.tara_category,
        },
        "personal_alignment_score": personal_score,
        "personal_band": band_value,
        "personal_breakdown": personal_breakdown,
    }


# -----------------------------
# Tara Bala / Birth Nakshatra
# -----------------------------

def _compute_birth_nakshatra(birth: BirthDetails, settings: guest.EngineSettings) -> Tuple[str, int]:
    import os
    from pathlib import Path
    ephe_path = os.environ.get("SWISSEPH_EPHE_PATH")
    if not ephe_path or not os.path.isdir(ephe_path):
        _default = Path(__file__).resolve().parent / "ephe"
        if _default.is_dir():
            ephe_path = str(_default)
    if ephe_path and os.path.isdir(ephe_path):
        import swisseph as swe
        swe.set_ephe_path(ephe_path)
    try:
        from jhora.panchanga import drik
        from jhora.panchanga.drik import Date as DrikDate, Place as DrikPlace
        from jhora.utils import julian_day_number
    except Exception as e:
        raise guest.EngineError(guest.EngineErrorCode.PYJHORA_ERROR, f"Failed to import PyJHora: {e}")
    try:
        if hasattr(drik, "set_ayanamsa_mode"):
            drik.set_ayanamsa_mode(settings.ayanamsa_mode)
    except Exception:
        pass
    pob = birth.place_of_birth
    pj_place = DrikPlace(pob.name or "BirthPlace", pob.lat, pob.lon, pob.tz)
    dt_local = birth.to_local_datetime()
    dob = DrikDate(dt_local.year, dt_local.month, dt_local.day)
    tob = (dt_local.hour, dt_local.minute, getattr(dt_local, "second", 0))
    jd_birth = julian_day_number(dob, tob)
    res = drik.nakshatra(jd_birth, pj_place)
    return _parse_nakshatra_result(res)


def _parse_nakshatra_result(res: Any) -> Tuple[str, int]:
    if isinstance(res, (list, tuple)):
        idx = None
        name = None
        if len(res) >= 1 and isinstance(res[0], int):
            idx = int(res[0])
        if len(res) >= 2:
            name = str(res[1])
        if idx is None:
            for x in res:
                if isinstance(x, int):
                    idx = int(x)
                    break
        if name is None:
            for x in res:
                if isinstance(x, str) and x.strip() and ":" not in x:
                    name = x.strip()
                    break
        if idx is None or name is None:
            raise guest.EngineError(guest.EngineErrorCode.PYJHORA_ERROR, f"Unrecognized nakshatra format: {res}")
        return (name, idx)
    raise guest.EngineError(guest.EngineErrorCode.PYJHORA_ERROR, f"Unrecognized nakshatra return: {res}")


def _todays_nakshatra(p: guest.PanchangaSnapshot) -> Tuple[str, int]:
    if not (p.nakshatra and getattr(p.nakshatra, "name", None) and getattr(p.nakshatra, "index", None)):
        raise guest.EngineError(guest.EngineErrorCode.INVALID_INPUT, "Missing today's nakshatra in Panchang")
    return (p.nakshatra.name, int(p.nakshatra.index))


def _compute_tara_bala(
    *,
    birth_nakshatra: str,
    birth_idx: int,
    today_nakshatra: str,
    today_idx: int,
) -> TaraBalaResult:
    delta = (today_idx - birth_idx) % 27
    tara_number = (delta % 9) + 1
    tara_names = {
        1: "Janma", 2: "Sampat", 3: "Vipat", 4: "Kshema", 5: "Pratyak",
        6: "Sadhana", 7: "Naidhana", 8: "Mitra", 9: "Parama Mitra",
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
# Nakshatra Personality (V1 minimal)
# -----------------------------

def _get_nakshatra_personality(nak_name: str, nak_idx: int) -> NakshatraPersonality:
    table: Dict[str, Dict[str, Any]] = {
        "Ashwini": {"ruling_planet": "Ketu", "symbol": "Horse head", "deity": "Ashvins", "keywords": ["speed", "healing", "beginnings"]},
        "Rohini": {"ruling_planet": "Moon", "symbol": "Chariot", "deity": "Brahma", "keywords": ["growth", "beauty", "creation"]},
        "Jyeshtha": {"ruling_planet": "Mercury", "symbol": "Earring / Umbrella", "deity": "Indra", "keywords": ["seniority", "protection", "leadership"]},
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
