"""
Event arbitration layer.

Applies suppression rules (from spec/events/compatibility.yaml) and
precedence ordering (from spec/events/precedence.yaml) to a merged event frame.

Returns ArbitrationResult:
  events    -- surviving events, potentially with adjusted tradeability scores
  suppressed -- hard-blocked events with suppression reason attached
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from project.spec_registry import load_yaml_relative

_SPEC_DIR = Path(__file__).resolve().parents[2] / "spec" / "events"


def load_compatibility_spec() -> Dict[str, Any]:
    return load_yaml_relative("spec/events/compatibility.yaml")


def load_precedence_spec() -> Dict[str, Any]:
    return load_yaml_relative("spec/events/precedence.yaml")


@dataclass
class ArbitrationResult:
    events: pd.DataFrame
    suppressed: pd.DataFrame = field(default_factory=pd.DataFrame)
    composite_events: pd.DataFrame = field(default_factory=pd.DataFrame)


def _events_overlap(
    df: pd.DataFrame, active_type: str, target_type: str, symbol: str
) -> bool:
    """True if any active_type event temporally overlaps any target_type event."""
    active = df[(df["event_type"] == active_type) & (df["symbol"] == symbol)]
    target = df[(df["event_type"] == target_type) & (df["symbol"] == symbol)]
    if active.empty or target.empty:
        return False
    for _, a in active.iterrows():
        a_enter = a.get("enter_ts", a["timestamp"])
        a_exit = a.get("exit_ts", a["timestamp"])
        for _, t in target.iterrows():
            if a_enter <= t["timestamp"] <= a_exit:
                return True
    return False


def arbitrate_events(
    df: pd.DataFrame,
    compat_spec: Dict[str, Any] | None = None,
    prec_spec: Dict[str, Any] | None = None,
) -> ArbitrationResult:
    """
    Apply suppression rules and precedence ordering to an event frame.

    Parameters
    ----------
    df : pd.DataFrame
        Event frame with: event_type, symbol, timestamp, enter_ts, exit_ts,
        event_tradeability_score.
    compat_spec, prec_spec : dict, optional
        Pre-loaded specs; loaded from file if None.

    Returns
    -------
    ArbitrationResult
    """
    if df.empty:
        return ArbitrationResult(events=df.copy(), suppressed=pd.DataFrame())

    if compat_spec is None:
        try:
            compat_spec = load_compatibility_spec()
        except Exception as e:
            warnings.warn(f"Cannot load compatibility spec: {e}; skipping arbitration")
            return ArbitrationResult(events=df.copy())

    if prec_spec is None:
        try:
            prec_spec = load_precedence_spec()
        except Exception as e:
            warnings.warn(f"Cannot load precedence spec: {e}; skipping precedence sort")
            prec_spec = {"family_precedence": [], "event_overrides": []}

    out = df.copy()
    suppressed_rows: List[pd.DataFrame] = []
    symbols = out["symbol"].unique() if "symbol" in out.columns else []

    for rule in compat_spec.get("suppression_rules", []):
        active_type = rule["when_active"]
        suppress_types = rule["suppress"]
        penalty = float(rule.get("penalty_factor", 0.5))
        hard_block = bool(rule.get("block", False))
        reason = rule.get("reason", "")

        for sym in symbols:
            for suppress_type in suppress_types:
                if not _events_overlap(out, active_type, suppress_type, sym):
                    continue
                mask = (out["event_type"] == suppress_type) & (out["symbol"] == sym)
                if not mask.any():
                    continue
                if hard_block:
                    blocked = out[mask].copy()
                    blocked["suppression_reason"] = reason
                    blocked["suppressed_by"] = active_type
                    suppressed_rows.append(blocked)
                    out = out[~mask].copy()
                elif "event_tradeability_score" in out.columns:
                    out.loc[mask, "event_tradeability_score"] = (
                        out.loc[mask, "event_tradeability_score"] * penalty
                    ).clip(0.0, 1.0)

    # Build priority lookup from precedence spec
    fam_prio = {e["family"]: e["priority"]
                for e in prec_spec.get("family_precedence", [])}
    evt_prio = {e["event_type"]: e["override_priority"]
                for e in prec_spec.get("event_overrides", [])}

    def _priority(row) -> int:
        et = str(row.get("event_type", ""))
        fam = str(row.get("canonical_family", ""))
        return evt_prio.get(et, fam_prio.get(fam, 999))

    if not out.empty:
        out["_arb_prio"] = out.apply(_priority, axis=1)
        out = out.sort_values(
            ["symbol", "timestamp", "_arb_prio"], ignore_index=True
        ).drop(columns=["_arb_prio"])

    suppressed_df = (
        pd.concat(suppressed_rows, ignore_index=True)
        if suppressed_rows else pd.DataFrame()
    )
    return ArbitrationResult(events=out, suppressed=suppressed_df)
