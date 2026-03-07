# engine.py
"""
Lyra Alignment Engine — typed stubs (PyJHora-based Panchang + deterministic scoring)

This file defines:
- Dataclasses & enums for the engine contract
- Function signatures required by Lyra (Home/Day Details/Heatmap)
- A clean separation between:
  1) Panchang extraction (PyJHora integration boundary)
  2) Scoring (pure deterministic logic)
  3) Packaging output (UI contract)

Implementation notes:
- compute_panchanga() is the only place that should import/use PyJHora.
- scoring functions must remain pure and unit-testable (no PyJHora dependency).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Tuple, Literal
import json
from pathlib import Path


# -------------------------
# Enums
# -------------------------

class RegionMode(str, Enum):
    NORTH_INDIA = "NORTH_INDIA"
    SOUTH_INDIA = "SOUTH_INDIA"


class AnchorMode(str, Enum):
    SUNRISE = "SUNRISE"
    NOW = "NOW"


class Band(str, Enum):
    CHALLENGING = "CHALLENGING"
    CAUTION = "CAUTION"
    NEUTRAL = "NEUTRAL"
    POSITIVE = "POSITIVE"
    FAVORABLE = "FAVORABLE"


# NOTE: Keep as string to pass-through to PyJHora (avoid mismatch)
AyanamsaMode = str


# -------------------------
# Errors
# -------------------------

class EngineErrorCode(str, Enum):
    INVALID_DATE = "INVALID_DATE"
    INVALID_PLACE = "INVALID_PLACE"
    INVALID_INPUT = "INVALID_INPUT"
    PANCHANGA_FAILED = "PANCHANGA_FAILED"
    PYJHORA_ERROR = "PYJHORA_ERROR"
    CONFIG_MISSING = "CONFIG_MISSING"
    CONFIG_INVALID = "CONFIG_INVALID"
    INTERNAL = "INTERNAL"


@dataclass(frozen=True)
class EngineError(Exception):
    code: EngineErrorCode
    message: str
    details: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


# -------------------------
# Core data types
# -------------------------

@dataclass(frozen=True)
class Place:
    """Geographic place for Panchang computation."""
    lat: float
    lon: float
    tz: float  # timezone offset hours, e.g., India=5.5
    name: Optional[str] = None


MonthSystem = Literal["AMANTA", "PURNIMANTA"]
Paksha = Literal["Shukla", "Krishna"]


@dataclass(frozen=True)
class EngineSettings:
    """User-configurable settings for computation."""
    region_mode: RegionMode
    anchor: AnchorMode = AnchorMode.SUNRISE
    ayanamsa_mode: AyanamsaMode = "LAHIRI"
    month_system_override: Optional[MonthSystem] = None  # for future flexibility


@dataclass(frozen=True)
class TithiInfo:
    index: int          # 1..30
    name: str           # canonical, e.g. "Krishna Tritiya"
    ends_at: str        # "HH:MM" local time


@dataclass(frozen=True)
class NakshatraInfo:
    index: int          # 1..27
    name: str           # canonical, e.g. "Rohini"
    ends_at: str        # "HH:MM" local time


@dataclass(frozen=True)
class YogaInfo:
    index: int          # 1..27
    name: str           # canonical, e.g. "Shubha"
    ends_at: str        # "HH:MM" local time


@dataclass(frozen=True)
class KaranaInfo:
    name: str           # canonical, e.g. "Bava"
    ends_at: str        # "HH:MM" local time


@dataclass(frozen=True)
class LunarMonthInfo:
    name: str           # canonical, e.g. "Magha"
    system: MonthSystem


@dataclass(frozen=True)
class PanchangaSnapshot:
    """
    Normalized Panchang payload at the chosen anchor time (typically sunrise).
    This structure should be stable and UI-ready.
    """
    date: str
    place: Place
    anchor: AnchorMode

    sunrise: str        # "HH:MM"
    sunset: str         # "HH:MM"
    vaara: str          # "Monday".."Sunday"

    tithi: TithiInfo
    nakshatra: NakshatraInfo
    yoga: YogaInfo
    karana: KaranaInfo

    paksha: Paksha
    lunar_month: LunarMonthInfo

    # Optional future additions (planner/time windows)
    # rahu_kalam: Optional[Tuple[str, str]] = None


@dataclass(frozen=True)
class ScoreBreakdownItem:
    factor: Literal["TITHI", "NAKSHATRA", "YOGA", "KARANA", "VAARA", "RAHU_DAY_PENALTY", "TARA_BALA"]
    value: int
    label: str


@dataclass(frozen=True)
class ScoreResult:
    alignment_score: int  # 0..100
    band: Band
    breakdown: List[ScoreBreakdownItem]
    summary: List[str]    # 1–2 lines


@dataclass(frozen=True)
class DayResult:
    date: str
    place: Place
    anchor: AnchorMode
    panchanga: PanchangaSnapshot
    score: ScoreResult
    summary_lines: List[str] = field(default_factory=list)  # alias for score.summary; for profile API


@dataclass(frozen=True)
class HeatmapDay:
    date: str
    score: int
    band: Band
    tithi_index: int
    nakshatra_index: int


# -------------------------
# Weights config
# -------------------------

BandRange = Tuple[int, int]


@dataclass(frozen=True)
class WeightsConfig:
    base_score: int
    rahu_day_penalty: int

    tithi_weights: Mapping[int, int]          # 1..30
    nakshatra_weights: Mapping[str, int]      # canonical names
    yoga_weights: Mapping[str, int]           # canonical names
    karana_weights: Mapping[str, int]         # canonical names
    vaara_weights: Mapping[str, int]          # "Monday".."Sunday"

    bands: Mapping[Band, BandRange]


def load_weights_config(path: str | Path) -> WeightsConfig:
    """
    Load weights config from YAML or JSON.

    Supported: .yaml / .yml (PyYAML) or .json
    """
    p = Path(path)
    if not p.exists():
        raise EngineError(EngineErrorCode.CONFIG_MISSING, f"Config not found: {p}")

    suffix = p.suffix.lower()
    if suffix in (".yaml", ".yml"):
        try:
            import yaml
            raw = yaml.safe_load(p.read_text(encoding="utf-8"))
        except Exception as e:
            raise EngineError(EngineErrorCode.CONFIG_INVALID, "Failed to parse YAML config", {"error": str(e)})
    else:
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            raise EngineError(EngineErrorCode.CONFIG_INVALID, "Failed to parse JSON config", {"error": str(e)})

    if raw is None:
        raise EngineError(EngineErrorCode.CONFIG_INVALID, "Config file is empty")

    try:
        bands_raw: Dict[str, List[int]] = raw["bands"]
        bands: Dict[Band, BandRange] = {
            Band(k): (int(v[0]), int(v[1])) for k, v in bands_raw.items()
        }

        tithi_raw: Dict[str, Any] = raw["tithi_weights"]
        tithi_weights: Dict[int, int] = {int(k): int(v) for k, v in tithi_raw.items()}

        return WeightsConfig(
            base_score=int(raw["base_score"]),
            rahu_day_penalty=int(raw["rahu_day_penalty"]),
            tithi_weights=tithi_weights,
            nakshatra_weights={str(k): int(v) for k, v in raw["nakshatra_weights"].items()},
            yoga_weights={str(k): int(v) for k, v in raw["yoga_weights"].items()},
            karana_weights={str(k): int(v) for k, v in raw["karana_weights"].items()},
            vaara_weights={str(k): int(v) for k, v in raw["vaara_weights"].items()},
            bands=bands,
        )
    except KeyError as e:
        raise EngineError(EngineErrorCode.CONFIG_INVALID, "Missing required config key", {"missing_key": str(e)})
    except Exception as e:
        raise EngineError(EngineErrorCode.CONFIG_INVALID, "Invalid config format", {"error": str(e)})


# -------------------------
# Primary APIs (App calls)
# -------------------------

def compute_day(
    date_yyyy_mm_dd: str,
    place: Place,
    settings: EngineSettings,
    weights: WeightsConfig,
) -> DayResult:
    """
    Compute one day: Panchang snapshot + deterministic score.

    - Panchang is computed at settings.anchor (default SUNRISE) using PyJHora.
    - Month system is chosen via settings.region_mode unless overridden.
    - Score is computed using weights config.
    """
    p = compute_panchanga(date_yyyy_mm_dd, place, settings)
    s = compute_alignment_score(p, weights)
    return build_day_result(p, s)


def compute_range(
    start_date_yyyy_mm_dd: str,
    end_date_yyyy_mm_dd: str,
    place: Place,
    settings: EngineSettings,
    weights: WeightsConfig,
) -> List[DayResult]:
    """
    Compute a range of days (inclusive end date).
    """
    from datetime import datetime, timedelta
    start = datetime.strptime(start_date_yyyy_mm_dd, "%Y-%m-%d").date()
    end = datetime.strptime(end_date_yyyy_mm_dd, "%Y-%m-%d").date()
    results: List[DayResult] = []
    current = start
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        results.append(compute_day(date_str, place, settings, weights))
        current += timedelta(days=1)
    return results


def compute_heatmap(
    start_date_yyyy_mm_dd: str,
    end_date_yyyy_mm_dd: str,
    place: Place,
    settings: EngineSettings,
    weights: WeightsConfig,
) -> List[HeatmapDay]:
    """
    Lightweight batch for calendar heatmap.
    """
    from datetime import datetime, timedelta
    start = datetime.strptime(start_date_yyyy_mm_dd, "%Y-%m-%d").date()
    end = datetime.strptime(end_date_yyyy_mm_dd, "%Y-%m-%d").date()
    results: List[HeatmapDay] = []
    current = start
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        day_result = compute_day(date_str, place, settings, weights)
        results.append(
            HeatmapDay(
                date=date_str,
                score=day_result.score.alignment_score,
                band=day_result.score.band,
                tithi_index=day_result.panchanga.tithi.index,
                nakshatra_index=day_result.panchanga.nakshatra.index,
            ),
        )
        current += timedelta(days=1)
    return results


# -------------------------
# PyJHora boundary
# -------------------------

def _safe_drik(func, *args, **kwargs):
    """Safely call a PyJHora drik function; raise EngineError on failure."""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        raise EngineError(
            EngineErrorCode.PANCHANGA_FAILED,
            f"Panchang computation failed: {e}",
            details={"function": getattr(func, "__name__", "?"), "error": str(e)},
        ) from e


def compute_panchanga(
    date_yyyy_mm_dd: str,
    place: Place,
    settings: EngineSettings,
) -> PanchangaSnapshot:
    """
    Compute Panchang at the configured anchor using PyJHora.
    Uses sunrise JD for AnchorMode.SUNRISE.
    """
    import os
    from pathlib import Path
    ephe_path = os.environ.get("SWISSEPH_EPHE_PATH")
    if not ephe_path or not os.path.isdir(ephe_path):
        # Default: prodbackend/ephe (next to this file)
        _default = Path(__file__).resolve().parent / "ephe"
        if _default.is_dir():
            ephe_path = str(_default)
    if ephe_path and os.path.isdir(ephe_path):
        import swisseph as swe
        swe.set_ephe_path(ephe_path)
    from jhora.panchanga import drik
    from jhora.panchanga.drik import Date as DrikDate, Place as DrikPlace
    from jhora.utils import julian_day_number

    parts = date_yyyy_mm_dd.strip().split("-")
    if len(parts) != 3:
        raise EngineError(EngineErrorCode.INVALID_DATE, f"Invalid date format: {date_yyyy_mm_dd}. Use YYYY-MM-DD.")
    try:
        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        raise EngineError(EngineErrorCode.INVALID_DATE, f"Invalid date: {date_yyyy_mm_dd}")

    dob = DrikDate(year, month, day)
    # Use 6:00 local as approximate "day start" to get sunrise for this date
    tob_approx = (6, 0, 0)
    jd_approx = julian_day_number(dob, tob_approx)
    drik_place = DrikPlace(place.name or "Place", place.lat, place.lon, place.tz)

    # Get sunrise time for this date; use its JD as anchor for SUNRISE
    sunrise_data = _safe_drik(drik.sunrise, jd_approx, drik_place)
    if isinstance(sunrise_data, (list, tuple)) and len(sunrise_data) >= 1:
        jd = float(sunrise_data[0])
    else:
        jd = jd_approx

    sunset_data = _safe_drik(drik.sunset, jd_approx, drik_place)
    sunrise_str = "06:00"
    sunset_str = "18:00"
    if isinstance(sunrise_data, (list, tuple)) and len(sunrise_data) >= 2:
        t = sunrise_data[1]
        if hasattr(t, "hour"):
            sunrise_str = f"{t.hour:02d}:{t.minute:02d}"
        else:
            sunrise_str = str(t)[:5] if len(str(t)) >= 5 else "06:00"
    if isinstance(sunset_data, (list, tuple)) and len(sunset_data) >= 2:
        t = sunset_data[1]
        if hasattr(t, "hour"):
            sunset_str = f"{t.hour:02d}:{t.minute:02d}"
        else:
            sunset_str = str(t)[:5] if len(str(t)) >= 5 else "18:00"

    # Vaara (0=Sunday .. 6=Saturday)
    vaara_data = _safe_drik(drik.vaara, jd)
    vaara_num = int(vaara_data) if isinstance(vaara_data, (int, float)) else 0
    if not 0 <= vaara_num <= 6:
        vaara_num = 0
    vaara = canonicalize_weekday(str(vaara_num))

    # Tithi
    tithi_data = _safe_drik(drik.tithi, jd, drik_place)
    tithi_num = 1
    tithi_ends = "00:00"
    if isinstance(tithi_data, (list, tuple)) and len(tithi_data) >= 1:
        tithi_num = int(tithi_data[0])
        if not 1 <= tithi_num <= 30:
            tithi_num = max(1, min(30, tithi_num))
        if len(tithi_data) >= 3:
            tithi_ends = _float_hours_to_time(float(tithi_data[2]))
    tithi_name = TITHI_NAMES[tithi_num - 1] if 1 <= tithi_num <= 30 else f"Tithi-{tithi_num}"
    paksha: Paksha = "Shukla" if tithi_num <= 15 else "Krishna"
    tithi_label = f"{paksha} {tithi_name}" if tithi_num != 15 and tithi_num != 30 else tithi_name
    tithi_info = TithiInfo(index=tithi_num, name=tithi_label, ends_at=tithi_ends)

    # Nakshatra
    nakshatra_data = _safe_drik(drik.nakshatra, jd, drik_place)
    nak_num = 1
    nak_ends = "00:00"
    if isinstance(nakshatra_data, (list, tuple)) and len(nakshatra_data) >= 1:
        nak_num = int(nakshatra_data[0])
        if not 1 <= nak_num <= 27:
            nak_num = max(1, min(27, nak_num))
        if len(nakshatra_data) >= 4:
            nak_ends = _float_hours_to_time(float(nakshatra_data[3]))
    nak_canonical = NAKSHATRA_CANONICAL[nak_num - 1] if 1 <= nak_num <= 27 else "Ashwini"
    nakshatra_info = NakshatraInfo(index=nak_num, name=nak_canonical, ends_at=nak_ends)

    # Yoga
    yoga_data = _safe_drik(drik.yogam, jd, drik_place)
    yoga_num = 1
    yoga_ends = "00:00"
    yoga_name_canon = YOGA_CANONICAL[0]
    if isinstance(yoga_data, (list, tuple)) and len(yoga_data) >= 1:
        yoga_num = int(yoga_data[0])
        if not 1 <= yoga_num <= 27:
            yoga_num = max(1, min(27, yoga_num))
        yoga_name_canon = YOGA_CANONICAL[yoga_num - 1] if 1 <= yoga_num <= 27 else YOGA_CANONICAL[0]
        if len(yoga_data) >= 3:
            yoga_ends = _float_hours_to_time(float(yoga_data[2]))
    else:
        yoga_name_canon = canonicalize_yoga(str(yoga_data))
    yoga_info = YogaInfo(index=yoga_num, name=yoga_name_canon, ends_at=yoga_ends)

    # Karana
    karana_data = _safe_drik(drik.karana, jd, drik_place)
    karana_name_canon = KARANA_CANONICAL[0]
    karana_ends = "00:00"
    if isinstance(karana_data, (list, tuple)) and len(karana_data) >= 1:
        first = karana_data[0]
        try:
            idx = int(first)
            if 1 <= idx <= 11:
                karana_name_canon = KARANA_CANONICAL[idx - 1]
            else:
                karana_name_canon = canonicalize_karana(str(first))
        except (TypeError, ValueError):
            karana_name_canon = canonicalize_karana(str(first))
        if len(karana_data) >= 2:
            karana_ends = _float_hours_to_time(float(karana_data[1]))
    else:
        karana_name_canon = canonicalize_karana(str(karana_data))
    if karana_name_canon in ("-1", "0") or not karana_name_canon.strip():
        karana_name_canon = KARANA_CANONICAL[0]
    karana_info = KaranaInfo(name=karana_name_canon, ends_at=karana_ends)

    # Lunar month
    month_sys = resolve_month_system(settings)
    month_data = _safe_drik(drik.lunar_month, jd, drik_place)
    m_idx = 1
    if isinstance(month_data, (list, tuple)) and len(month_data) >= 1:
        m_idx = int(month_data[0])
        if not 1 <= m_idx <= 12:
            m_idx = max(1, min(12, m_idx))
    lunar_month_name = LUNAR_MONTH_NAMES[m_idx - 1] if 1 <= m_idx <= 12 else "Chaitra"
    lunar_month_info = LunarMonthInfo(name=lunar_month_name, system=month_sys)

    return PanchangaSnapshot(
        date=date_yyyy_mm_dd,
        place=place,
        anchor=settings.anchor,
        sunrise=sunrise_str,
        sunset=sunset_str,
        vaara=vaara,
        tithi=tithi_info,
        nakshatra=nakshatra_info,
        yoga=yoga_info,
        karana=karana_info,
        paksha=paksha,
        lunar_month=lunar_month_info,
    )


# -------------------------
# Scoring (pure deterministic)
# -------------------------

# -------------------------
# Scoring (pure deterministic)
# -------------------------

def compute_alignment_score(
    p: PanchangaSnapshot,
    weights: WeightsConfig,
    *,
    has_rahu_kalam: bool = True,
) -> ScoreResult:
    """
    Compute deterministic day alignment score from normalized Panchang.
    """
    base = weights.base_score
    tithi_w = weights.tithi_weights.get(p.tithi.index, 0)
    nak_w = weights.nakshatra_weights.get(p.nakshatra.name, 0)
    yoga_w = weights.yoga_weights.get(p.yoga.name, 0)
    karana_w = weights.karana_weights.get(p.karana.name, 0)
    vaara_w = weights.vaara_weights.get(p.vaara, 0)
    rahu_penalty = weights.rahu_day_penalty if has_rahu_kalam else 0

    raw = base + tithi_w + nak_w + yoga_w + karana_w + vaara_w + rahu_penalty
    score = clamp_score(raw)
    band = classify_band(score, weights)

    breakdown: List[ScoreBreakdownItem] = [
        ScoreBreakdownItem("TITHI", tithi_w, p.tithi.name),
        ScoreBreakdownItem("NAKSHATRA", nak_w, p.nakshatra.name),
        ScoreBreakdownItem("YOGA", yoga_w, p.yoga.name),
        ScoreBreakdownItem("KARANA", karana_w, p.karana.name),
        ScoreBreakdownItem("VAARA", vaara_w, p.vaara),
    ]
    if has_rahu_kalam and weights.rahu_day_penalty != 0:
        breakdown.append(
            ScoreBreakdownItem("RAHU_DAY_PENALTY", weights.rahu_day_penalty, "Rahu exists"),
        )

    # Summary lines via text_engine
    try:
        from text_engine import generate_summary
        panchanga_dict = {
            "tithi_index": p.tithi.index,
            "nakshatra": p.nakshatra.name,
            "yoga": p.yoga.name,
            "karana": p.karana.name,
            "vaara": p.vaara,
        }
        score_dict = {
            "alignment_score": score,
            "band": band.value,
            "breakdown": [{"factor": b.factor, "value": b.value, "label": b.label} for b in breakdown],
        }
        summary = generate_summary(panchanga_dict, score_dict, has_rahu_kalam=has_rahu_kalam)
    except Exception:
        summary = [f"Alignment score: {score} ({band.value}).", "Keep pacing steady."]

    return ScoreResult(
        alignment_score=score,
        band=band,
        breakdown=breakdown,
        summary=summary,
    )


def classify_band(score: int, weights: WeightsConfig) -> Band:
    """Return Band based on configured score ranges."""
    for band, (lo, hi) in weights.bands.items():
        if lo <= score <= hi:
            return band
    # Fallback if config incomplete
    if score >= 75:
        return Band.FAVORABLE
    if score >= 55:
        return Band.POSITIVE
    if score >= 40:
        return Band.NEUTRAL
    if score >= 25:
        return Band.CAUTION
    return Band.CHALLENGING


def clamp_score(score: int) -> int:
    """Clamp integer score to 0..100."""
    return max(0, min(100, int(score)))


# -------------------------
# Packaging
# -------------------------

def build_day_result(p: PanchangaSnapshot, s: ScoreResult) -> DayResult:
    """Package a PanchangaSnapshot + ScoreResult into final DayResult contract."""
    return DayResult(
        date=p.date,
        place=p.place,
        anchor=p.anchor,
        panchanga=p,
        score=s,
        summary_lines=list(s.summary) if s.summary else [],
    )


# -------------------------
# Normalization helpers (recommended)
# -------------------------

# Canonical names matching weights_balanced.yaml (order by index 1..27 or 1..11)
NAKSHATRA_CANONICAL = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashirsha",
    "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha",
    "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati",
    "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha",
    "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
]
# PyJHora / common spelling -> canonical
NAKSHATRA_ALIASES = {
    "mrigashira": "Mrigashirsha", "mrigashirsha": "Mrigashirsha",
    "shatabhisha": "Shatabhisha", "sathabhisha": "Shatabhisha", "satabhisha": "Shatabhisha",
    "purva phalguni": "Purva Phalguni", "uttara phalguni": "Uttara Phalguni",
    "purva ashadha": "Purva Ashadha", "uttara ashadha": "Uttara Ashadha",
    "purva bhadrapada": "Purva Bhadrapada", "uttara bhadrapada": "Uttara Bhadrapada",
}
YOGA_CANONICAL = [
    "Vishkambha", "Priti", "Ayushman", "Saubhagya", "Shobhana", "Atiganda",
    "Sukarman", "Dhriti", "Shoola", "Ganda", "Vriddhi", "Dhruva",
    "Vyaghata", "Harshana", "Vajra", "Siddhi", "Vyatipata", "Variyana",
    "Parigha", "Shiva", "Siddha", "Sadhya", "Shubha", "Shukla", "Brahma", "Indra", "Vaidhriti",
]
KARANA_CANONICAL = [
    "Bava", "Balava", "Kaulava", "Taitila", "Gara", "Vanija",
    "Vishti", "Shakuni", "Chatushpada", "Naga", "Kimstughna",
]
VAARA_CANONICAL = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
TITHI_NAMES = [
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima",
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Amavasya",
]
LUNAR_MONTH_NAMES = [
    "Chaitra", "Vaishakha", "Jyeshtha", "Ashadha", "Shravana",
    "Bhadrapada", "Ashvina", "Kartika", "Margashirsha", "Pushya",
    "Magha", "Phalguna",
]


def canonicalize_weekday(name: str) -> str:
    """
    Normalize weekday to "Monday".."Sunday".
    Accepts: 0-6 (as str/int), "Ravivara (Sunday)", "Monday", "mon", etc.
    """
    if name is None or (isinstance(name, str) and not name.strip()):
        return "Monday"
    s = str(name).strip()
    if s.isdigit() and 0 <= int(s) <= 6:
        return VAARA_CANONICAL[int(s)]
    lower = s.lower()
    for canon in VAARA_CANONICAL:
        if canon.lower() in lower or lower in canon.lower():
            return canon
    if "sun" in lower or "ravivar" in lower:
        return "Sunday"
    if "mon" in lower and "day" in lower:
        return "Monday"
    if "tue" in lower or "mangal" in lower:
        return "Tuesday"
    if "wed" in lower or "budh" in lower:
        return "Wednesday"
    if "thu" in lower or "guru" in lower:
        return "Thursday"
    if "fri" in lower or "shukra" in lower:
        return "Friday"
    if "sat" in lower or "shani" in lower:
        return "Saturday"
    return VAARA_CANONICAL[1]  # default Monday


def canonicalize_nakshatra(name: str) -> str:
    """
    Normalize nakshatra names to canonical keys used in weights config.
    """
    if not name:
        return NAKSHATRA_CANONICAL[0]
    s = str(name).strip()
    if s.isdigit() and 1 <= int(s) <= 27:
        return NAKSHATRA_CANONICAL[int(s) - 1]
    lower = s.lower().replace(" ", "")
    for canon in NAKSHATRA_CANONICAL:
        if canon.lower().replace(" ", "") == lower:
            return canon
    key = lower.replace(" ", "")
    if key in NAKSHATRA_ALIASES:
        return NAKSHATRA_ALIASES[key]
    for k, v in NAKSHATRA_ALIASES.items():
        if k in key or key in k:
            return v
    return s.title()


def canonicalize_yoga(name: str) -> str:
    """Normalize yoga names to canonical keys used in weights config."""
    if not name:
        return YOGA_CANONICAL[0]
    s = str(name).strip()
    if s.isdigit() and 1 <= int(s) <= 27:
        return YOGA_CANONICAL[int(s) - 1]
    lower = s.lower()
    for canon in YOGA_CANONICAL:
        if canon.lower() == lower:
            return canon
    return s.title()


def canonicalize_karana(name: str) -> str:
    """Normalize karana names to canonical keys used in weights config."""
    if not name:
        return KARANA_CANONICAL[0]
    s = str(name).strip()
    if s.isdigit() and 1 <= int(s) <= 11:
        return KARANA_CANONICAL[int(s) - 1]
    lower = s.lower()
    for canon in KARANA_CANONICAL:
        if canon.lower() == lower:
            return canon
    if "bhadra" in lower or "vishti" in lower:
        return "Vishti"
    return s.title()


def _float_hours_to_time(fh: float) -> str:
    """Convert float hours (e.g. 7.05) to 'HH:MM'. Normalize to 0-24."""
    try:
        fh = float(fh)
        while fh < 0:
            fh += 24
        while fh >= 24:
            fh -= 24
        h = int(fh) % 24
        m = max(0, min(59, int((fh - int(fh)) * 60)))
        return f"{h:02d}:{m:02d}"
    except Exception:
        return "00:00"


def resolve_month_system(settings: EngineSettings) -> MonthSystem:
    """
    Resolve lunar month system:
    - If month_system_override is set, use it.
    - Else: NORTH_INDIA => PURNIMANTA, SOUTH_INDIA => AMANTA.
    """
    if settings.month_system_override is not None:
        return settings.month_system_override
    return "PURNIMANTA" if settings.region_mode == RegionMode.NORTH_INDIA else "AMANTA"