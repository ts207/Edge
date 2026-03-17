from __future__ import annotations

import logging
from typing import Dict, Any

import numpy as np

_LOG = logging.getLogger(__name__)

def calculate_portfolio_risk_multiplier(
    gross_exposure: float,
    max_gross_leverage: float,
    target_vol: float,
    current_vol: float,
) -> float:
    """
    Calculate risk multiplier based on portfolio constraints and volatility.
    """
    # Leverage constraint
    leverage_cap = max(0.0, 1.0 - (gross_exposure / max_gross_leverage)) if max_gross_leverage > 0 else 0.0
    
    # Volatility scaling
    vol_scale = target_vol / max(1e-6, current_vol)
    
    risk_mult = min(1.0, leverage_cap, vol_scale)
    return float(np.clip(risk_mult, 0.0, 1.0))

def get_asset_correlation_adjustment(
    asset_bucket: str,
    bucket_exposures: Dict[str, float],
    correlation_limit: float = 0.5,
) -> float:
    """
    Reduce sizing if correlated exposure is already high.
    """
    current_bucket_exposure = bucket_exposures.get(asset_bucket, 0.0)
    if current_bucket_exposure > correlation_limit:
        return 0.5 # Simple 50% reduction
    return 1.0
