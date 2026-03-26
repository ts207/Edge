from __future__ import annotations

EVENT_ALIASES = {
    "BASIS_DISLOCATION": "BASIS_DISLOC",
    "VOL_REGIME_SHIFT": "VOL_REGIME_SHIFT_EVENT",
    "DEPTH_COLLAPSE": "DEPTH_STRESS_PROXY",
    "ABSORPTION_EVENT": "ABSORPTION_PROXY",
}


def resolve_event_alias(event_type: str) -> str:
    normalized = str(event_type).strip().upper()
    return EVENT_ALIASES.get(normalized, normalized)
