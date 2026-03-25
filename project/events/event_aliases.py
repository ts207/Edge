from __future__ import annotations

EVENT_ALIASES = {
    "BASIS_DISLOCATION": "BASIS_DISLOC",
    "VOL_REGIME_SHIFT": "VOL_REGIME_SHIFT_EVENT",
    "ORDERFLOW_IMBALANCE_SHOCK": "PRICE_VOL_IMBALANCE_PROXY",
    "DEPTH_COLLAPSE": "DEPTH_STRESS_PROXY",
    "SWEEP_STOPRUN": "WICK_REVERSAL_PROXY",
    "ABSORPTION_EVENT": "ABSORPTION_PROXY",
    "FORCED_FLOW_EXHAUSTION": "FLOW_EXHAUSTION_PROXY",
    "SPREAD_BLOWOUT": "SPREAD_STRESS_PROXY",
}


def resolve_event_alias(event_type: str) -> str:
    normalized = str(event_type).strip().upper()
    return EVENT_ALIASES.get(normalized, normalized)
