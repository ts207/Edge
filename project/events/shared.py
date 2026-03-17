from __future__ import annotations

import pandas as pd
from typing import Dict, Any, List

from project.events.emission import emit_canonical_event, to_event_row

EVENT_COLUMNS = [
    "event_type",
    "event_id",
    "symbol",
    "anchor_ts",
    "eval_bar_ts",
    "enter_ts",
    "detected_ts",
    "signal_ts",
    "exit_ts",
    "event_idx",
    "year",
    "event_score",
    "evt_signal_intensity",
    "severity_bucket",
    "direction",
    "sign",
    "basis_z",
    "spread_z",
    "funding_rate_bps",
    "carry_state",
    "ms_trend_state",
    "ms_spread_state",
    "features_payload",
]

def format_event_id(event_type: str, symbol: str, idx: int, sub_idx: int = 0) -> str:
    return f"{event_type.lower()}_{symbol}_{idx:08d}_{sub_idx:03d}"

def emit_event(
    *,
    event_type: str,
    symbol: str,
    event_id: str,
    eval_bar_ts: pd.Timestamp,
    direction: str = "non_directional",
    sign: int = 0,
    intensity: float = 1.0,
    severity: str = "moderate",
    metadata: Dict[str, Any] | None = None,
    shift_bars: int = 0,
    timeframe_minutes: int = 5,
) -> Dict[str, Any]:
    """
    Standardize event emission under the milestone-2 PIT policy.

    ``shift_bars`` now means *additional* bars of delay beyond the mandatory
    next-bar signal. ``shift_bars=0`` therefore emits ``signal_ts`` on the next
    tradable bar after ``eval_bar_ts``.
    """
    record = emit_canonical_event(
        event_type=event_type,
        asset=symbol,
        eval_bar_ts=eval_bar_ts,
        event_id=event_id,
        intensity=float(intensity),
        severity=severity,
        meta=dict(metadata or {}),
        timeframe_minutes=timeframe_minutes,
        signal_delay_bars=max(int(shift_bars), 0) + 1,
    )
    return to_event_row(
        record,
        symbol=symbol,
        direction=direction,
        sign=sign,
        severity_label=severity,
    )
