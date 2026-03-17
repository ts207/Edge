"""
Event quality scoring layer.

Sub-scores (each in [0, 1], higher = more tradeable):
  severity_score      -- signal intensity percentile rank within frame
  cleanliness_score   -- isolation from nearby co-occurring events
  crowding_score      -- inverted basis_z (low basis = less crowded)
  execution_score     -- inverted spread_z (low spread = easier execution)
  novelty_score       -- unusualness vs recent local history (sigmoid of z-score)
  microstructure_score -- depth and imbalance confirmation (penalizes phantom liquidity)

Aggregate:
  event_tradeability_score = non-linear combination of sub-scores (exponential reward)
"""
from __future__ import annotations

from typing import List

import numpy as np
import pandas as pd

EventScoreColumns: List[str] = [
    "severity_score",
    "cleanliness_score",
    "crowding_score",
    "execution_score",
    "novelty_score",
    "microstructure_score",
    "event_tradeability_score",
]

_NOVELTY_LOOKBACK = 20
_CLEANLINESS_LOOKBACK = 5

def _minmax_normalize(series: pd.Series) -> pd.Series:
    lo, hi = series.min(), series.max()
    if hi == lo:
        return pd.Series(0.5, index=series.index)
    return ((series - lo) / (hi - lo)).clip(0.0, 1.0)

def _severity_score(df: pd.DataFrame) -> pd.Series:
    # Use non-linear scaling for severity (e.g. squaring the percentile) to reward extreme signals
    intensity = df["evt_signal_intensity"].astype(float).fillna(0.0)
    percentile = intensity.rank(pct=True).clip(0.0, 1.0)
    return np.power(percentile, 1.5) # Non-linear reward

def _cleanliness_score(df: pd.DataFrame) -> pd.Series:
    result = pd.Series(1.0, index=df.index)
    for sym, grp in df.groupby("symbol", sort=False):
        idx = grp.index
        n = len(idx)
        counts = np.ones(n, dtype=float)
        for k in range(n):
            lo = max(0, k - _CLEANLINESS_LOOKBACK)
            hi = min(n, k + _CLEANLINESS_LOOKBACK + 1)
            counts[k] = float(hi - lo - 1)
        max_neighbors = max(counts.max(), 1.0)
        result.loc[idx] = 1.0 - (counts / max_neighbors)
    return result.clip(0.0, 1.0)

def _crowding_score(df: pd.DataFrame) -> pd.Series:
    if "basis_z" not in df.columns:
        return pd.Series(0.5, index=df.index)
    abs_basis = df["basis_z"].abs().astype(float).fillna(0.0)
    # Penalize high crowding exponentially
    crowdedness = _minmax_normalize(abs_basis)
    return (1.0 - np.power(crowdedness, 2.0)).clip(0.0, 1.0)

def _execution_score(df: pd.DataFrame) -> pd.Series:
    if "spread_z" not in df.columns:
        return pd.Series(0.5, index=df.index)
    spread = df["spread_z"].astype(float).fillna(0.0).clip(lower=0.0)
    # Penalize wide spreads exponentially
    normalized_spread = _minmax_normalize(spread)
    return (1.0 - np.power(normalized_spread, 1.5)).clip(0.0, 1.0)

def _microstructure_score(df: pd.DataFrame) -> pd.Series:
    """
    Rewards events that occur during high-depth, high-engagement periods.
    Penalizes events occurring in thin air (phantom liquidity).
    """
    score = pd.Series(0.5, index=df.index)
    has_depth = "depth_usd" in df.columns
    has_vol = "quote_volume" in df.columns
    
    if has_depth and has_vol:
        depth = df["depth_usd"].astype(float).fillna(0.0)
        vol = df["quote_volume"].astype(float).fillna(0.0)
        
        # High depth + high volume = strong microstructure
        combined = (depth * vol).apply(np.sqrt)
        score = _minmax_normalize(combined)
    elif has_vol:
        vol = df["quote_volume"].astype(float).fillna(0.0)
        score = _minmax_normalize(vol)
        
    return score.clip(0.0, 1.0)

def _novelty_score(df: pd.DataFrame) -> pd.Series:
    result = pd.Series(0.5, index=df.index)
    intensity = df["evt_signal_intensity"].astype(float).fillna(0.0)
    group_keys = [k for k in ("event_type", "symbol") if k in df.columns]
    if not group_keys:
        return result
    for _, grp in df.groupby(group_keys, sort=False):
        idx = grp.index
        vals = intensity.loc[idx].values
        n = len(vals)
        scores = np.full(n, 0.5)
        # Using EWMA approach for regime-adjusted baselines instead of static rolling
        alpha = 2.0 / (_NOVELTY_LOOKBACK + 1.0)
        mu = vals[0] if n > 0 else 0.0
        var = 0.0
        
        for k in range(n):
            val = vals[k]
            diff = val - mu
            inc = alpha * diff
            mu += inc
            var = (1 - alpha) * (var + diff * inc)
            sigma = np.sqrt(var)
            
            if sigma < 1e-10:
                scores[k] = 0.5
            else:
                z = (val - mu) / sigma
                # Sigmoid non-linear mapping
                scores[k] = float(1.0 / (1.0 + np.exp(-z)))
        result.loc[idx] = scores
    return result.clip(0.0, 1.0)

def score_event_frame(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute quality sub-scores and aggregate tradeability score for an event frame.
    """
    out = df.copy()
    if out.empty:
        for col in EventScoreColumns:
            out[col] = pd.Series(dtype=float)
        return out

    out["severity_score"] = _severity_score(out).values
    out["cleanliness_score"] = _cleanliness_score(out).values
    out["crowding_score"] = _crowding_score(out).values
    out["execution_score"] = _execution_score(out).values
    out["novelty_score"] = _novelty_score(out).values
    out["microstructure_score"] = _microstructure_score(out).values
    
    # Non-linear aggregate: require baseline viability across all fronts, 
    # but reward exceptional severity and novelty
    base_viability = (
        out["cleanliness_score"] * 
        out["crowding_score"] * 
        out["execution_score"] * 
        out["microstructure_score"]
    ).apply(lambda x: np.power(x, 0.25)) # Geometric mean of viability conditions
    
    # Final score combines viability with signal strength
    out["event_tradeability_score"] = (base_viability * out["severity_score"] * out["novelty_score"]).apply(np.sqrt).clip(0.0, 1.0)
    
    return out
