# project/research/search/evaluator_utils.py
"""
Shared utilities for hypothesis evaluation.
Broken out from evaluator.py to avoid circular imports.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from project.core.constants import HORIZON_BARS_BY_TIMEFRAME, horizon_bars_for_label
from project.domain.compiled_registry import get_domain_registry
from project.domain.hypotheses import HypothesisSpec, TriggerType
from project.core.column_registry import ColumnRegistry
from project.events.event_specs import EVENT_REGISTRY_SPECS

log = logging.getLogger(__name__)


def horizon_bars(horizon: str) -> int:
    h = horizon.lower().strip()
    if h not in HORIZON_BARS_BY_TIMEFRAME:
        raise ValueError(
            f"Unknown horizon: {horizon!r}. Supported: {list(HORIZON_BARS_BY_TIMEFRAME.keys())}"
        )
    return horizon_bars_for_label(h)


def forward_log_returns(close: pd.Series, horizon_bars: int) -> pd.Series:
    log_close = np.log(close.clip(lower=1e-12))
    return log_close.shift(-horizon_bars) - log_close


def excursion_stats(
    close: pd.Series, 
    mask: pd.Series, 
    horizon_bars: int, 
    direction_sign: float
) -> Tuple[pd.Series, pd.Series]:
    """
    Calculate Max Adverse Excursion (MAE) and Max Favorable Excursion (MFE)
    for each trigger event in the mask.
    """
    if not mask.any():
        return pd.Series(dtype=float), pd.Series(dtype=float)
    
    indices = np.where(mask)[0]
    maes = []
    mfes = []
    
    close_vals = close.values
    for idx in indices:
        if idx + horizon_bars >= len(close_vals):
            maes.append(np.nan)
            mfes.append(np.nan)
            continue
            
        window = close_vals[idx : idx + horizon_bars + 1]
        returns = np.log(window / close_vals[idx])
        signed_returns = returns * direction_sign
        
        maes.append(np.nanmin(signed_returns))
        mfes.append(np.nanmax(signed_returns))
        
    return pd.Series(maes, index=mask[mask].index), pd.Series(mfes, index=mask[mask].index)


def trigger_mask(spec: HypothesisSpec, features: pd.DataFrame) -> pd.Series:
    """
    Resolve a trigger to a boolean mask over the feature table rows.
    Returns a Series[bool] aligned to features.index.
    """
    t = spec.trigger
    ttype = t.trigger_type
    false_mask = pd.Series(False, index=features.index)

    if ttype == TriggerType.EVENT:
        eid = t.event_id or ""
        spec_event = EVENT_REGISTRY_SPECS.get(eid.upper())
        signal_col = spec_event.signal_column if spec_event else None
        cols = ColumnRegistry.event_cols(eid, signal_col=signal_col)
        for col in cols:
            if col in features.columns:
                vals = features[col]
                return vals.where(vals.notna(), False).astype(bool)
        log.debug("Event column for %r (signal_col=%r) not found in features", eid, signal_col)
        return false_mask

    if ttype == TriggerType.STATE:
        cols = ColumnRegistry.state_cols(t.state_id or "")
        for col in cols:
            if col in features.columns:
                vals = pd.to_numeric(features[col], errors="coerce")
                vals = vals.where(vals.notna(), 0)
                return (vals == 1) if t.state_active else (vals == 0)
        log.debug("State column for %r not found in features", t.state_id)
        return false_mask

    if ttype == TriggerType.TRANSITION:
        from_cols = ColumnRegistry.state_cols(t.from_state or "")
        to_cols = ColumnRegistry.state_cols(t.to_state or "")
        from_col = next((c for c in from_cols if c in features.columns), None)
        to_col = next((c for c in to_cols if c in features.columns), None)
        if from_col and to_col:
            was_from_vals = pd.to_numeric(features[from_col], errors="coerce")
            was_from = was_from_vals.where(was_from_vals.notna(), 0).shift(1) == 1
            is_to_vals = pd.to_numeric(features[to_col], errors="coerce")
            is_to = is_to_vals.where(is_to_vals.notna(), 0) == 1
            return was_from & is_to
        log.debug(
            "Transition columns for %r→%r not found in features",
            t.from_state, t.to_state,
        )
        return false_mask

    if ttype == TriggerType.FEATURE_PREDICATE:
        feat_name = t.feature or ""
        cols = ColumnRegistry.feature_cols(feat_name)
        feat = next((c for c in cols if c in features.columns), None)
        if not feat:
            log.debug("Feature %r not found in features", feat_name)
            return false_mask
        vals = pd.to_numeric(features[feat], errors="coerce")
        op, thr = t.operator, t.threshold
        if op == ">=": return vals >= thr
        if op == "<=": return vals <= thr
        if op == ">":  return vals > thr
        if op == "<":  return vals < thr
        if op == "==": return vals == thr
        return false_mask

    if ttype == TriggerType.SEQUENCE:
        cols = ColumnRegistry.sequence_cols(t.sequence_id or "")
        for col in cols:
            if col in features.columns:
                vals = features[col]
                return vals.where(vals.notna(), False).astype(bool)
        log.debug("Sequence column for %r not found in features", t.sequence_id)
        return false_mask

    if ttype == TriggerType.INTERACTION:
        cols = ColumnRegistry.interaction_cols(t.interaction_id or "")
        for col in cols:
            if col in features.columns:
                vals = features[col]
                return vals.where(vals.notna(), False).astype(bool)
        log.debug("Interaction column for %r not found in features", t.interaction_id)
        return false_mask

    return false_mask


def load_context_state_map() -> Dict[Tuple[str, str], str]:
    """
    Load state_registry.yaml and return a flat mapping of (family, label) -> state_id.
    Raises FileNotFoundError if registry is missing.
    """
    registry = get_domain_registry()
    if not registry.context_state_map:
        raise FileNotFoundError("context_state_map is missing from compiled domain registry")
    return dict(registry.context_state_map)


# Cache for the context state map to avoid repeated file I/O
_CACHED_CONTEXT_MAP: Optional[Dict[Tuple[str, str], str]] = None


def context_mask(context: Dict[str, str], features: pd.DataFrame) -> Optional[pd.Series]:
    """
    Build a boolean mask from a context dict (e.g. {vol_regime: "high", carry_state: "funding_pos"}).
    Returns None if ANY context key cannot be resolved to a feature column (context is unresolvable).
    Returns a combined AND mask when all keys resolve.
    """
    global _CACHED_CONTEXT_MAP
    if _CACHED_CONTEXT_MAP is None:
        try:
            _CACHED_CONTEXT_MAP = load_context_state_map()
        except Exception as e:
            log.error("Failed to load context state map: %s", e)
            return None

    combined = pd.Series(True, index=features.index)
    for family, label in context.items():
        state_id = _CACHED_CONTEXT_MAP.get((family, label))
        if state_id is None:
            log.debug("No state mapping for context (%r, %r) — context unresolvable", family, label)
            return None
        cols = ColumnRegistry.state_cols(state_id)
        col = next((c for c in cols if c in features.columns), None)
        if col is None:
            log.debug("Context state column %r not found in features — context unresolvable", state_id)
            return None
        vals = pd.to_numeric(features[col], errors="coerce").fillna(0)
        combined = combined & (vals == 1)
    return combined


def trigger_key(spec: HypothesisSpec) -> str:
    return spec.trigger.label()
