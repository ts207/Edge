from __future__ import annotations

EVENT_ALIASES = {
    "BASIS_DISLOCATION": "BASIS_DISLOC",
    "VOL_REGIME_SHIFT": "VOL_REGIME_SHIFT_EVENT",
}


def resolve_event_alias(event_type: str) -> str:
    normalized = str(event_type).strip().upper()
    return EVENT_ALIASES.get(normalized, normalized)
