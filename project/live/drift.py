from __future__ import annotations

import logging
from typing import Dict, Any, List

import numpy as np
import pandas as pd

_LOG = logging.getLogger(__name__)

def calculate_feature_drift(
    research_feature_samples: pd.Series,
    live_feature_samples: pd.Series,
    threshold: float = 0.2,
) -> Dict[str, Any]:
    """
    Calculate drift using Population Stability Index (PSI) or JS Divergence.
    """
    if research_feature_samples.empty or live_feature_samples.empty:
        return {}
        
    # Simplified drift check: Z-score of mean
    res_mean = research_feature_samples.mean()
    res_std = research_feature_samples.std()
    live_mean = live_feature_samples.mean()
    
    drift_score = abs(live_mean - res_mean) / max(1e-6, res_std)
    
    return {
        "drift_score": float(drift_score),
        "is_drifting": bool(drift_score > threshold * 3.0), # Example threshold scaling
        "research_mean": float(res_mean),
        "live_mean": float(live_mean),
    }

def monitor_execution_drift(
    research_slippage_bps: float,
    live_slippage_bps: float,
    research_fill_rate: float,
    live_fill_rate: float,
) -> Dict[str, Any]:
    """
    Monitor if execution conditions are worse than research assumptions.
    """
    slippage_drift = live_slippage_bps / max(1.0, research_slippage_bps)
    fill_rate_drift = live_fill_rate / max(1e-6, research_fill_rate)
    
    return {
        "slippage_drift_ratio": float(slippage_drift),
        "fill_rate_drift_ratio": float(fill_rate_drift),
        "alert": bool(slippage_drift > 2.0 or fill_rate_drift < 0.5),
    }
