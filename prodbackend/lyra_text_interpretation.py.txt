# lyra_text_interpretation.py
"""
Lyra Text Interpretation Engine (No AI, deterministic, self-contained)

What it does:
- Generates 2 short Home-screen summary lines from Panchang + score breakdown.
- Uses deterministic rule tables (tunable in code).
- Designed to be easy for an intern: call generate_summary(...) and display result.

How to use (minimal):
    lines = generate_summary(
        panchanga={
            "tithi_index": 18,
            "nakshatra": "Rohini",
            "yoga": "Shubha",
            "karana": "Bava",
            "vaara": "Tuesday"
        },
        score={
            "alignment_score": 69,
            "band": "POSITIVE",
            "breakdown": [
                {"factor": "TITHI", "value": 7, "label": "Krishna Tritiya"},
                {"factor": "NAKSHATRA", "value": 7, "label": "Rohini"},
                {"factor": "YOGA", "value": 6, "label": "Shubha"},
                {"factor": "KARANA", "value": 3, "label": "Bava"},
                {"factor": "VAARA", "value": -2, "label": "Tuesday"},
                {"factor": "RAHU_DAY_PENALTY", "value": -1, "label": "Rahu exists"},
            ]
        },
        rahu_window=("09:10", "10:40"),
    )

Notes:
- This module does NOT compute Panchang. It only turns inputs into text.
- Works with dict inputs (recommended for simplicity).
- If you have dataclasses (from engine.py), you can pass them too; this module
  will read attributes if dict keys are not present.

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Iterable, Sequence

# ------------------------------------------------------------
# Tunable text tables
# ------------------------------------------------------------

TONE_BY_BAND: Dict[str, str] = {
    "FAVORABLE": "Strong alignment for steady progress.",
    "POSITIVE": "Supportive day for focused work.",
    "NEUTRAL": "Balanced day—steady, with a few watch-outs.",
    "CAUTION": "Proceed with care—keep decisions simple.",
    "CHALLENGING": "Keep the day light and avoid big commitments.",
}

LINE1_TEMPLATES: Dict[str, str] = {
    "FAVORABLE": "{tone} Good for {tag1} and {tag2}.",
    "POSITIVE": "{tone} Good for {tag1}.",
    "NEUTRAL": "{tone} Good for {tag1}; keep pace steady.",
    "CAUTION": "{tone} Prefer {tag1} over big changes.",
    "CHALLENGING": "{tone} Stick to {tag1}.",
}

# Tag suggestions from each factor "strength"
# These are intentionally generic (non-predictive) and calm.
TITHI_TAG_BY_WEIGHT: Dict[int, List[str]] = {
    7: ["decisive action", "starting tasks"],
    6: ["steady execution", "progress"],
    5: ["planning", "communication"],
    4: ["organizing", "follow-through"],
    3: ["learning", "meetings"],
    0: ["routine work"],
    -2: ["reflection", "resetting"],
    -3: ["rest", "closure"],
    -5: ["small tasks", "avoid rushing"],
    -6: ["keep it simple", "avoid major starts"],
    -7: ["pause and review", "avoid commitments"],
}

NAKSHATRA_TAG_BY_WEIGHT: Dict[int, List[str]] = {
    7: ["growth", "relationships"],
    6: ["collaboration", "public-facing work"],
    5: ["learning", "steady progress"],
    4: ["initiatives", "movement"],
    3: ["creative work", "exploration"],
    2: ["execution", "problem-solving"],
    1: ["routine work"],
    0: ["neutral flow"],
    -3: ["work quietly", "avoid conflict"],
    -4: ["double-check details", "avoid confrontations"],
    -5: ["keep plans flexible", "avoid big starts"],
    -7: ["stay conservative", "avoid commitments"],
}

YOGA_TAG_BY_WEIGHT: Dict[int, List[str]] = {
    6: ["clarity", "auspicious momentum"],
    5: ["smooth coordination", "productivity"],
    4: ["steady outcomes"],
    3: ["patience", "stability"],
    2: ["light progress"],
    0: ["neutral flow"],
    -2: ["avoid overextending"],
    -3: ["reduce risk", "avoid haste"],
    -7: ["keep it simple", "avoid major decisions"],
    -8: ["stay conservative", "avoid major decisions"],
    -10: ["stay conservative", "avoid major decisions"],
}

VAARA_TAGS: Dict[str, List[str]] = {
    "Monday": ["planning", "care work"],
    "Tuesday": ["focus", "controlled action"],
    "Wednesday": ["communication", "transactions"],
    "Thursday": ["learning", "guidance"],
    "Friday": ["relationships", "comfort"],
    "Saturday": ["discipline", "long-term work"],
    "Sunday": ["reset", "visibility"],
}

# Primary caution priority (choose one):
# 1) Strong negative Yoga (Vaidhriti/Vyatipata or any <= -7)
# 2) Vishti Karana
# 3) Harsh Nakshatra (<= -4)
# 4) Rahu guidance
NEGATIVE_YOGAS_HARD = {"Vyatipata", "Vaidhriti"}  # canonical names

# Caution templates
CAUTION_STRONG = "Avoid major decisions today; keep actions simple."
CAUTION_VISHTI = "Avoid high-stakes actions while Vishti (Bhadra) is active."
CAUTION_NAK = "Avoid confrontations; double-check details."
CAUTION_RAHU = "Avoid critical actions during Rahu Kalam{window}."

# Some defaults if tags are missing
DEFAULT_GOOD_TAGS = ["routine work", "planning", "steady progress"]


# ------------------------------------------------------------
# Minimal helpers (work with dicts or objects)
# ------------------------------------------------------------

def _get(obj: Any, path: str, default: Any = None) -> Any:
    """
    Read value from dict/object using dot paths.
    Examples:
        _get(p, "tithi_index")
        _get(p, "tithi.index")
    """
    cur = obj
    for part in path.split("."):
        if cur is None:
            return default
        if isinstance(cur, dict):
            if part in cur:
                cur = cur[part]
            else:
                return default
        else:
            if hasattr(cur, part):
                cur = getattr(cur, part)
            else:
                return default
    return cur


def _normalize_band(band: Any, score_value: int) -> str:
    if isinstance(band, str) and band.strip():
        b = band.strip().upper()
        # allow some minor variants
        mapping = {"FAVOURABLE": "FAVORABLE"}
        return mapping.get(b, b)
    # If band missing, classify from score
    if score_value >= 75:
        return "FAVORABLE"
    if score_value >= 55:
        return "POSITIVE"
    if score_value >= 40:
        return "NEUTRAL"
    if score_value >= 25:
        return "CAUTION"
    return "CHALLENGING"


def _dedupe_keep_order(items: Sequence[str]) -> List[str]:
    seen = set()
    out = []
    for x in items:
        x2 = x.strip()
        if not x2 or x2 in seen:
            continue
        seen.add(x2)
        out.append(x2)
    return out


def _closest_weight_key(table: Dict[int, List[str]], w: int) -> int:
    """
    Our mapping tables are sparse (e.g., only 7,6,5,...).
    Choose the nearest existing key to weight w.
    """
    keys = sorted(table.keys())
    # exact
    if w in table:
        return w
    # nearest by absolute difference; tie -> higher (more positive) for positives, lower for negatives
    best = keys[0]
    best_d = abs(w - best)
    for k in keys[1:]:
        d = abs(w - k)
        if d < best_d:
            best, best_d = k, d
        elif d == best_d:
            # tie-breaker
            if w >= 0 and k > best:
                best = k
            if w < 0 and k < best:
                best = k
    return best


def _extract_breakdown(score: Any) -> List[Dict[str, Any]]:
    bd = _get(score, "breakdown", default=[])
    if isinstance(bd, list):
        # ensure dicts
        out = []
        for it in bd:
            if isinstance(it, dict):
                out.append(it)
            else:
                # maybe dataclass-like
                out.append({
                    "factor": _get(it, "factor"),
                    "value": _get(it, "value"),
                    "label": _get(it, "label", default=""),
                })
        return out
    return []


def _find_factor_value(breakdown: List[Dict[str, Any]], factor: str) -> Optional[int]:
    for it in breakdown:
        if str(it.get("factor", "")).upper() == factor:
            try:
                return int(it.get("value", 0))
            except Exception:
                return None
    return None


# ------------------------------------------------------------
# Public API
# ------------------------------------------------------------

def generate_summary(
    panchanga: Any,
    score: Any,
    *,
    rahu_window: Optional[Tuple[str, str]] = None,
    has_rahu_kalam: Optional[bool] = None,
) -> List[str]:
    """
    Return exactly 2 lines for the Home screen.

    Inputs:
      - panchanga: dict/object with at least:
          tithi_index (int) OR tithi.index
          nakshatra (str) OR nakshatra.name
          yoga (str) OR yoga.name
          karana (str) OR karana.name
          vaara (str)
      - score: dict/object with:
          alignment_score (int)
          band (str) OR omit band
          breakdown (list[{factor,value,label}]) recommended
      - rahu_window: ("HH:MM","HH:MM") optional; if provided, appended in line 2
      - has_rahu_kalam: optional bool override (defaults to True if not specified)

    Deterministic rules:
      - Select tone from band
      - Select 1–2 positive tags from biggest positive contributors
      - Select 1 primary caution based on Yoga/Karana/Nakshatra, else Rahu
    """
    score_value = int(_get(score, "alignment_score", default=0) or 0)
    band_raw = _get(score, "band", default=None)
    band = _normalize_band(band_raw, score_value)

    tone = TONE_BY_BAND.get(band, "Balanced day—steady, with a few watch-outs.")
    template = LINE1_TEMPLATES.get(band, "{tone} Good for {tag1}.")

    breakdown = _extract_breakdown(score)

    # Determine weights/contributions (prefer breakdown values)
    tithi_w = _find_factor_value(breakdown, "TITHI")
    nak_w = _find_factor_value(breakdown, "NAKSHATRA")
    yoga_w = _find_factor_value(breakdown, "YOGA")

    # Extract basic panchanga strings
    tithi_index = _get(panchanga, "tithi_index", default=None)
    if tithi_index is None:
        tithi_index = _get(panchanga, "tithi.index", default=None)

    nak_name = _get(panchanga, "nakshatra", default=None)
    if nak_name is None:
        nak_name = _get(panchanga, "nakshatra.name", default=None)

    yoga_name = _get(panchanga, "yoga", default=None)
    if yoga_name is None:
        yoga_name = _get(panchanga, "yoga.name", default=None)

    karana_name = _get(panchanga, "karana", default=None)
    if karana_name is None:
        karana_name = _get(panchanga, "karana.name", default=None)

    vaara = _get(panchanga, "vaara", default=None)

    # Build candidate tags from top contributors
    # Approach: sort positive breakdown factors by contribution
    positive_factors = []
    for it in breakdown:
        try:
            val = int(it.get("value", 0))
        except Exception:
            continue
        fac = str(it.get("factor", "")).upper()
        if val > 0 and fac in {"TITHI", "NAKSHATRA", "YOGA", "VAARA"}:
            positive_factors.append((val, fac))
    positive_factors.sort(reverse=True, key=lambda x: x[0])

    tags: List[str] = []
    for _, fac in positive_factors:
        if fac == "TITHI" and tithi_w is not None:
            key = _closest_weight_key(TITHI_TAG_BY_WEIGHT, tithi_w)
            tags.extend(TITHI_TAG_BY_WEIGHT.get(key, []))
        elif fac == "NAKSHATRA" and nak_w is not None:
            key = _closest_weight_key(NAKSHATRA_TAG_BY_WEIGHT, nak_w)
            tags.extend(NAKSHATRA_TAG_BY_WEIGHT.get(key, []))
        elif fac == "YOGA" and yoga_w is not None:
            key = _closest_weight_key(YOGA_TAG_BY_WEIGHT, yoga_w)
            tags.extend(YOGA_TAG_BY_WEIGHT.get(key, []))
        elif fac == "VAARA" and isinstance(vaara, str):
            tags.extend(VAARA_TAGS.get(vaara.strip().title(), []))

    # If breakdown missing/empty, fall back to reasonable defaults from available fields
    if not tags:
        if isinstance(vaara, str):
            tags.extend(VAARA_TAGS.get(vaara.strip().title(), []))
        tags.extend(DEFAULT_GOOD_TAGS)

    tags = _dedupe_keep_order(tags)
    tag1 = tags[0] if tags else "routine work"
    tag2 = tags[1] if len(tags) > 1 else "steady progress"

    # Compose line 1
    if "{tag2}" in template:
        line1 = template.format(tone=tone, tag1=tag1, tag2=tag2)
    else:
        line1 = template.format(tone=tone, tag1=tag1)

    # Decide if Rahu exists (default True if not provided)
    if has_rahu_kalam is None:
        # If caller doesn't pass it, assume True (most days have Rahu Kalam)
        has_rahu_kalam = True

    # Compose line 2 using caution priority
    yoga_name_s = str(yoga_name or "").strip()
    karana_name_s = str(karana_name or "").strip()
    nak_weight_for_caution = nak_w if nak_w is not None else 0
    yoga_weight_for_caution = yoga_w if yoga_w is not None else 0

    if yoga_name_s in NEGATIVE_YOGAS_HARD or yoga_weight_for_caution <= -7:
        line2 = CAUTION_STRONG
    elif karana_name_s.lower() == "vishti":
        line2 = CAUTION_VISHTI
    elif nak_weight_for_caution <= -4:
        line2 = CAUTION_NAK
    else:
        if has_rahu_kalam:
            window = ""
            if rahu_window and len(rahu_window) == 2:
                window = f" ({rahu_window[0]}–{rahu_window[1]})"
            line2 = CAUTION_RAHU.format(window=window)
        else:
            # If no Rahu info at all, keep a gentle generic caution
            line2 = "Keep pacing steady and avoid rushing key decisions."

    # Hard limits: keep it short-ish (optional, safe)
    line1 = _trim_sentence(line1, max_len=110)
    line2 = _trim_sentence(line2, max_len=110)

    return [line1, line2]


def _trim_sentence(s: str, max_len: int = 110) -> str:
    s = " ".join(s.split())
    if len(s) <= max_len:
        return s
    # simple trim at last punctuation/space before limit
    cut = s.rfind(".", 0, max_len)
    if cut >= 40:
        return s[:cut + 1]
    cut = s.rfind(";", 0, max_len)
    if cut >= 40:
        return s[:cut + 1]
    cut = s.rfind(",", 0, max_len)
    if cut >= 40:
        return s[:cut] + "…"
    cut = s.rfind(" ", 0, max_len)
    if cut >= 40:
        return s[:cut] + "…"
    return s[: max_len - 1] + "…"


# ------------------------------------------------------------
# Quick demo run
# ------------------------------------------------------------

if __name__ == "__main__":
    p = {
        "tithi_index": 18,
        "nakshatra": "Rohini",
        "yoga": "Shubha",
        "karana": "Bava",
        "vaara": "Tuesday",
    }
    s = {
        "alignment_score": 69,
        "band": "POSITIVE",
        "breakdown": [
            {"factor": "TITHI", "value": 7, "label": "Krishna Tritiya"},
            {"factor": "NAKSHATRA", "value": 7, "label": "Rohini"},
            {"factor": "YOGA", "value": 6, "label": "Shubha"},
            {"factor": "KARANA", "value": 3, "label": "Bava"},
            {"factor": "VAARA", "value": -2, "label": "Tuesday"},
            {"factor": "RAHU_DAY_PENALTY", "value": -1, "label": "Rahu exists"},
        ],
    }
    lines = generate_summary(p, s, rahu_window=("09:10", "10:40"))
    for ln in lines:
        print("-", ln)