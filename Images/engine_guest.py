# engine_guest.py
"""
Lyra Guest Engine (PyJHora-based)

USE THIS FOR:
- Guest mode (no user birth details)
- Any screen that needs Panchang facts + guest alignment score

This module provides:
- compute_day()
- compute_range()
- compute_heatmap()

It also exposes FACT windows for:
- Rahu Kalam
- Yamaganda
- Gulika Kalam

Note:
PyJHora API signatures vary across versions. This file uses defensive parsing.
If you hit a PyJHora mismatch, adjust only:
- _extract_anga()
- _extract_window()
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import json

try:
    import yaml  # type: ignore
except Exception:
    yaml = None


# -----------------------------
# Enums / Errors
# -----------------------------

class RegionMode(str, Enum):
    NORTH_INDIA = "NORTH_INDIA"  # Purnimanta (typical North India display)
    SOUTH_INDIA = "SOUTH_INDIA"  # Amanta (typical South India display)


class AnchorMode(str, Enum):
    SUNRISE = "SUNRISE"
    NOW = "NOW"  # optional


class Band(str, Enum):
    CHALLENGING = "CHALLENGING"
    CAUTION = "CAUTION"
    NEUTRAL = "NEUTRAL"
    POSITIVE = "POSITIVE"
    FAVORABLE = "FAVORABLE"


class EngineErrorCode(str, Enum):
    INVALID_INPUT = "INVALID_INPUT"
    PYJHORA_ERROR = "PYJHORA_ERROR"
    CONFIG_ERROR = "CONFIG_ERROR"


@dataclass
class EngineError(Exception):
    code: EngineErrorCode
    message: str
    details: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        return f"{self.code.value}: {self.message}"


# -----------------------------
# Data models
# -----------------------------

@dataclass(frozen=True)
class Place:
    lat: float
    lon: float
    tz: float
    name: Optional[str] = None


@dataclass(frozen=True)
class EngineSettings:
    region_mode: RegionMode = RegionMode.NORTH_INDIA
    anchor: AnchorMode = AnchorMode.SUNRISE
    ayanamsa_mode: str = "LAHIRI"  # pass-through


@dataclass(frozen=True)
class AngaEnd:
    name: str
    index: Optional[int] = None
    ends_at: Optional[str] = None  # local "HH:MM"


@dataclass(frozen=True)
class LunarMonthInfo:
    name: Optional[str] = None
    system: Optional[str] = None  # "AMANTA" or "PURNIMANTA"


@dataclass(frozen=True)
class PanchangaSnapshot:
    date: str  # YYYY-MM-DD (civil date)
    place_name: str
    lat: float
    lon: float
    tz: float

    sunrise: Optional[str] = None
    sunset: Optional[str] = None

    vaara: Optional[str] = None
    paksha: Optional[str] = None

    tithi: Optional[AngaEnd] = None
    nakshatra: Optional[AngaEnd] = None
    yoga: Optional[AngaEnd] = None
    karana: Optional[AngaEnd] = None

    lunar_month: Optional[LunarMonthInfo] = None

    # Facts-only time windows
    rahu_kalam: Optional[Tuple[str, str]] = None
    yamaganda: Optional[Tuple[str, str]] = None
    gulika_kalam: Optional[Tuple[str, str]] = None


@dataclass(frozen=True)
class ScoreBreakdownItem:
    factor: str
    value: int
    label: str


@dataclass(frozen=True)
class ScoreResult:
    alignment_score: int
    band: Band
    breakdown: List[ScoreBreakdownItem]


@dataclass(frozen=True)
class DayResult:
    panchanga: PanchangaSnapshot
    score: ScoreResult
    summary_lines: List[str]  # deterministic; UI can ignore if it wants facts only


@dataclass(frozen=True)
class HeatmapDay:
    date: str
    score: int
    band: Band
    is_purnima: bool
    is_amavasya: bool


@dataclass(frozen=True)
class WeightsConfig:
    base_score: int
    rahu_day_penalty: int
    tithi_weights: Dict[int, int]
    nakshatra_weights: Dict[str, int]
    yoga_weights: Dict[str, int]
    karana_weights: Dict[str, int]
    vaara_weights: Dict[str, int]
    bands: Dict[Band, Tuple[int, int]]


# -----------------------------
# Weights loader (YAML/JSON)
# -----------------------------

def load_weights_config(path: str) -> WeightsConfig:
    try:
        if path.lower().endswith((".yaml", ".yml")):
            if yaml is None:
                raise EngineError(EngineErrorCode.CONFIG_ERROR, "pyyaml not installed but YAML weights provided")
            with open(path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f)
        else:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
    except EngineError:
        raise
    except Exception as e:
        raise EngineError(EngineErrorCode.CONFIG_ERROR, f"Failed to read weights: {e}")

    try:
        base_score = int(raw["base_score"])
        rahu_day_penalty = int(raw["rahu_day_penalty"])
        tithi_weights = {int(k): int(v) for k, v in raw["tithi_weights"].items()}
        nakshatra_weights = {str(k): int(v) for k, v in raw["nakshatra_weights"].items()}
        yoga_weights = {str(k): int(v) for k, v in raw["yoga_weights"].items()}
        karana_weights = {str(k): int(v) for k, v in raw["karana_weights"].items()}
        vaara_weights = {str(k): int(v) for k, v in raw["vaara_weights"].items()}

        bands: Dict[Band, Tuple[int, int]] = {}
        for k, v in raw["bands"].items():
            b = Band(str(k).upper())
            bands[b] = (int(v[0]), int(v[1]))

        # Basic validation
        for i in range(1, 31):
            if i not in tithi_weights:
                raise EngineError(EngineErrorCode.CONFIG_ERROR, f"Missing tithi weight: {i}")

        return WeightsConfig(
            base_score=base_score,
            rahu_day_penalty=rahu_day_penalty,
            tithi_weights=tithi_weights,
            nakshatra_weights=nakshatra_weights,
            yoga_weights=yoga_weights,
            karana_weights=karana_weights,
            vaara_weights=vaara_weights,
            bands=bands,
        )
    except EngineError:
        raise
    except Exception as e:
        raise EngineError(EngineErrorCode.CONFIG_ERROR, f"Invalid weights schema: {e}")


# -----------------------------
# Scoring
# -----------------------------

def classify_band(score: int, bands: Dict[Band, Tuple[int, int]]) -> Band:
    for b, (lo, hi) in bands.items():
        if lo <= score <= hi:
            return b
    if score >= 75:
        return Band.FAVORABLE
    if score >= 55:
        return Band.POSITIVE
    if score >= 40:
        return Band.NEUTRAL
    if score >= 25:
        return Band.CAUTION
    return Band.CHALLENGING


def compute_alignment_score(p: PanchangaSnapshot, w: WeightsConfig) -> ScoreResult:
    if not (p.tithi and p.tithi.index and p.nakshatra and p.yoga and p.karana and p.vaara):
        raise EngineError(EngineErrorCode.INVALID_INPUT, "Missing Panchang angas for scoring")

    tithi_idx = int(p.tithi.index)
    if not (1 <= tithi_idx <= 30):
        raise EngineError(EngineErrorCode.INVALID_INPUT, f"Invalid tithi index: {tithi_idx}")

    tithi_w = int(w.tithi_weights.get(tithi_idx, 0))
    nak_w = int(w.nakshatra_weights.get(p.nakshatra.name, 0))
    yoga_w = int(w.yoga_weights.get(p.yoga.name, 0))
    kar_w = int(w.karana_weights.get(p.karana.name, 0))
    vaar_w = int(w.vaara_weights.get(p.vaara, 0))

    breakdown = [
        ScoreBreakdownItem("BASE", w.base_score, "Base score"),
        ScoreBreakdownItem("TITHI", tithi_w, p.tithi.name),
        ScoreBreakdownItem("NAKSHATRA", nak_w, p.nakshatra.name),
        ScoreBreakdownItem("YOGA", yoga_w, p.yoga.name),
        ScoreBreakdownItem("KARANA", kar_w, p.karana.name),
        ScoreBreakdownItem("VAARA", vaar_w, p.vaara),
        ScoreBreakdownItem("RAHU_DAY_PENALTY", w.rahu_day_penalty, "Daily Rahu factor"),
    ]

    raw = w.base_score + tithi_w + nak_w + yoga_w + kar_w + vaar_w + w.rahu_day_penalty
    score = max(0, min(100, int(raw)))
    band = classify_band(score, w.bands)

    return ScoreResult(alignment_score=score, band=band, breakdown=breakdown)


# -----------------------------
# PyJHora extraction
# -----------------------------

def compute_panchanga(date_str: str, place: Place, settings: EngineSettings) -> PanchangaSnapshot:
    """
    Panchang facts for a civil date + location.

    Guest mode uses this directly.
    Profile mode also uses this for today's facts, but adds personalized overlays elsewhere.
    """
    try:
        req_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        raise EngineError(EngineErrorCode.INVALID_INPUT, "date must be YYYY-MM-DD", {"date": date_str})

    try:
        from jhora.panchanga import drik  # type: ignore
        from jhora import utils  # type: ignore
    except Exception as e:
        raise EngineError(EngineErrorCode.PYJHORA_ERROR, f"Failed to import PyJHora: {e}")

    place_name = place.name or "Lyra"
    snap = PanchangaSnapshot(
        date=date_str, place_name=place_name, lat=place.lat, lon=place.lon, tz=place.tz
    )

    try:
        pj_place = drik.Place(place_name, place.lat, place.lon, place.tz)

        # set ayanamsa if supported
        try:
            if hasattr(drik, "set_ayanamsa_mode"):
                drik.set_ayanamsa_mode(settings.ayanamsa_mode)
        except Exception:
            pass

        y, m, d = req_date.year, req_date.month, req_date.day
        try:
            jd0 = utils.gregorian_to_jd(drik.Date(y, m, d))
        except Exception:
            jd0 = utils.gregorian_to_jd((y, m, d))

        # anchor
        sunrise_jd = jd0
        try:
            sr = drik.sunrise(jd0, pj_place)
            snap = _replace(snap, sunrise=_fmt_hhmm(_safe_idx(sr, 0)))
            sunrise_jd = _safe_idx(sr, 2, default=jd0)
        except Exception:
            pass

        try:
            ss = drik.sunset(jd0, pj_place)
            snap = _replace(snap, sunset=_fmt_hhmm(_safe_idx(ss, 0)))
        except Exception:
            pass

        # weekday
        try:
            snap = _replace(snap, vaara=_normalize_weekday(drik.vaara(sunrise_jd, pj_place)))
        except Exception:
            pass

        # core angas
        snap = _replace(snap, tithi=_extract_anga(drik.tithi, sunrise_jd, pj_place, kind="tithi"))
        snap = _replace(snap, nakshatra=_extract_anga(drik.nakshatra, sunrise_jd, pj_place, kind="nakshatra"))
        snap = _replace(snap, yoga=_extract_anga(drik.yoga, sunrise_jd, pj_place, kind="yoga"))
        snap = _replace(snap, karana=_extract_anga(drik.karana, sunrise_jd, pj_place, kind="karana"))

        # paksha from tithi index
        if snap.tithi and snap.tithi.index:
            t = int(snap.tithi.index)
            paksha = "Shukla Paksha" if 1 <= t <= 15 else "Krishna Paksha"
            snap = _replace(snap, paksha=paksha)

        # lunar month (optional; display mode changes by region)
        month_system = "PURNIMANTA" if settings.region_mode == RegionMode.NORTH_INDIA else "AMANTA"
        lm = None
        try:
            if hasattr(drik, "lunar_month"):
                lm_raw = drik.lunar_month(sunrise_jd, pj_place, month_system=month_system)
                lm = _stringify_month(lm_raw)
        except Exception:
            lm = None
        snap = _replace(snap, lunar_month=LunarMonthInfo(name=lm, system=month_system))

        # kalam windows (facts)
        snap = _replace(snap, rahu_kalam=_extract_window(drik, "rahu_kalam", jd0, pj_place))
        snap = _replace(snap, yamaganda=_extract_window(drik, "yamaganda_kalam", jd0, pj_place) or _extract_window(drik, "yamagandam", jd0, pj_place))
        snap = _replace(snap, gulika_kalam=_extract_window(drik, "gulika_kalam", jd0, pj_place))

        return snap

    except EngineError:
        raise
    except Exception as e:
        raise EngineError(EngineErrorCode.PYJHORA_ERROR, f"PyJHora computation failed: {e}")


def _extract_anga(fn, jd: float, place_obj: Any, kind: str) -> AngaEnd:
    """
    Defensive extraction of (index, name, ends_at).
    Common patterns:
      tithi():     (idx, name, "HH:MM", end_jd, ...)
      nakshatra(): (idx, name, "HH:MM", end_jd, ...)
      yoga():      (idx, name, "HH:MM", end_jd, ...)
      karana():    varies; often (name, "HH:MM", end_jd) or (idx, name, "HH:MM"...)
    """
    res = fn(jd, place_obj)

    idx: Optional[int] = None
    name: Optional[str] = None
    ends_at: Optional[str] = None

    if isinstance(res, str):
        name = res

    elif isinstance(res, (list, tuple)):
        # Try typical patterns
        # 1) If first element int => index
        if len(res) >= 1 and isinstance(res[0], int):
            idx = int(res[0])
        # 2) Find first non-empty string as name (skip HH:MM strings if possible)
        for item in res:
            if isinstance(item, str) and item.strip():
                s = item.strip()
                if ":" in s and len(s) >= 4:
                    continue
                name = s
                break
        # 3) Find time string
        for item in res:
            if isinstance(item, str) and ":" in item:
                ends_at = _fmt_hhmm(item)
                break

        # For some returns where name is at position 1
        if name is None and len(res) >= 2 and isinstance(res[1], str):
            name = res[1].strip()

        # If time is at position 2
        if ends_at is None and len(res) >= 3 and isinstance(res[2], str) and ":" in res[2]:
            ends_at = _fmt_hhmm(res[2])

    if name is None:
        name = f"Unknown {kind}"

    return AngaEnd(name=name, index=idx, ends_at=ends_at)


def _extract_window(drik_mod: Any, fn_name: str, jd0: float, place_obj: Any) -> Optional[Tuple[str, str]]:
    try:
        fn = getattr(drik_mod, fn_name, None)
        if fn is None:
            return None
        r = fn(jd0, place_obj)
        if isinstance(r, (list, tuple)) and len(r) >= 2:
            a = _fmt_hhmm(r[0]) or ""
            b = _fmt_hhmm(r[1]) or ""
            if a and b:
                return (a, b)
        return None
    except Exception:
        return None


def _safe_idx(x: Any, i: int, default: Any = None) -> Any:
    if isinstance(x, (list, tuple)) and len(x) > i:
        return x[i]
    return default


def _fmt_hhmm(x: Any) -> Optional[str]:
    if x is None:
        return None
    s = str(x).strip()
    if len(s) >= 5 and s[2] == ":":
        return s[:5]
    return s


def _normalize_weekday(v: Any) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, int):
        names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        return names[v] if 0 <= v < 7 else str(v)
    s = str(v).strip()
    map3 = {"Sun": "Sunday", "Mon": "Monday", "Tue": "Tuesday", "Wed": "Wednesday",
            "Thu": "Thursday", "Fri": "Friday", "Sat": "Saturday"}
    return map3.get(s, s)


def _stringify_month(lm_raw: Any) -> Optional[str]:
    if lm_raw is None:
        return None
    if isinstance(lm_raw, str):
        return lm_raw
    if isinstance(lm_raw, (list, tuple)) and lm_raw:
        return str(lm_raw[0])
    return str(lm_raw)


def _replace(obj, **kwargs):
    # dataclass replace without importing dataclasses.replace (keeps code simple)
    d = dict(obj.__dict__)
    d.update(kwargs)
    return obj.__class__(**d)


# -----------------------------
# Public Guest APIs
# -----------------------------

def compute_day(date_str: str, place: Place, settings: EngineSettings, weights: WeightsConfig) -> DayResult:
    """
    Guest mode day result.

    UI calls:
      /day -> this
    """
    from lyra_text_interpretation import generate_summary  # uses your existing module

    p = compute_panchanga(date_str, place, settings)
    s = compute_alignment_score(p, weights)

    summary = generate_summary(
        panchanga={
            "tithi_index": p.tithi.index if p.tithi else None,
            "nakshatra": p.nakshatra.name if p.nakshatra else None,
            "yoga": p.yoga.name if p.yoga else None,
            "karana": p.karana.name if p.karana else None,
            "vaara": p.vaara,
        },
        score={
            "alignment_score": s.alignment_score,
            "band": s.band.value,
            "breakdown": [{"factor": b.factor, "value": b.value, "label": b.label} for b in s.breakdown],
        },
        rahu_window=p.rahu_kalam,
    )

    return DayResult(panchanga=p, score=s, summary_lines=summary)


def compute_range(start: str, end: str, place: Place, settings: EngineSettings, weights: WeightsConfig) -> List[DayResult]:
    d1 = datetime.strptime(start, "%Y-%m-%d").date()
    d2 = datetime.strptime(end, "%Y-%m-%d").date()
    if d2 < d1:
        raise EngineError(EngineErrorCode.INVALID_INPUT, "end must be >= start")
    out: List[DayResult] = []
    cur = d1
    while cur <= d2:
        out.append(compute_day(cur.isoformat(), place, settings, weights))
        cur += timedelta(days=1)
    return out


def compute_heatmap(start: str, end: str, place: Place, settings: EngineSettings, weights: WeightsConfig) -> List[HeatmapDay]:
    d1 = datetime.strptime(start, "%Y-%m-%d").date()
    d2 = datetime.strptime(end, "%Y-%m-%d").date()
    if d2 < d1:
        raise EngineError(EngineErrorCode.INVALID_INPUT, "end must be >= start")
    out: List[HeatmapDay] = []
    cur = d1
    while cur <= d2:
        p = compute_panchanga(cur.isoformat(), place, settings)
        s = compute_alignment_score(p, weights)
        is_purnima = bool(p.tithi and p.tithi.index == 15)
        is_amavasya = bool(p.tithi and p.tithi.index == 30)
        out.append(HeatmapDay(date=cur.isoformat(), score=s.alignment_score, band=s.band,
                              is_purnima=is_purnima, is_amavasya=is_amavasya))
        cur += timedelta(days=1)
    return out