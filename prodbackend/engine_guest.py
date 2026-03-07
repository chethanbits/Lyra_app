# engine_guest.py
"""
Lyra Guest Engine — re-exports from engine.py for app_v2 and engine_profile.
Keeps guest mode (location-only) logic in one place; profile mode wraps this.
"""
from engine import (
    Place,
    EngineSettings,
    RegionMode,
    AnchorMode,
    Band,
    EngineError,
    EngineErrorCode,
    WeightsConfig,
    load_weights_config,
    compute_day,
    compute_range,
    compute_heatmap,
    classify_band,
    ScoreBreakdownItem,
    PanchangaSnapshot,
    ScoreResult,
    DayResult,
)

__all__ = [
    "Place",
    "EngineSettings",
    "RegionMode",
    "AnchorMode",
    "Band",
    "EngineError",
    "EngineErrorCode",
    "WeightsConfig",
    "load_weights_config",
    "compute_day",
    "compute_range",
    "compute_heatmap",
    "classify_band",
    "ScoreBreakdownItem",
    "PanchangaSnapshot",
    "ScoreResult",
    "DayResult",
]
