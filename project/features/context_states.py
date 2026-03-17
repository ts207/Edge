import pandas as pd
import numpy as np
from project.contracts.temporal_contracts import TemporalContract
from project.core.causal_primitives import (
    trailing_quantile,
    trailing_median,
    trailing_mean,
    trailing_std,
    trailing_percentile_rank,
)

# --- Temporal Contract ---

TEMPORAL_CONTRACT = TemporalContract(
    name="context_states",
    output_mode="point_feature",
    observation_clock="bar_close",
    decision_lag_bars=1,
    lookback_bars=288,
    uses_current_observation=False,
    calibration_mode="rolling",
    fit_scope="streaming",
    approved_primitives=("trailing_quantile", "trailing_median", "trailing_mean", "trailing_std"),
    notes="Contextual state indicators (Vol, Liq, OI, Funding, Trend, Spread). All trailing."
)

def calculate_ms_vol_state(rv_pct: pd.Series) -> pd.Series:
    """
    Volatility Dimension:
    0: LOW (0-33%)
    1: MID (33-66%)
    2: HIGH (66-95%)
    3: SHOCK (>95%)
    """
    bins = [0.0, 33.0, 66.0, 95.0, 100.0]
    labels = [0.0, 1.0, 2.0, 3.0]
    return pd.cut(rv_pct, bins=bins, labels=labels, include_lowest=True).astype(float)

def calculate_ms_liq_state(quote_volume: pd.Series, window: int = 288) -> pd.Series:
    """
    Liquidity Dimension based on rolling 24h quote volume quantiles:
    0: THIN (Bottom 20%)
    1: NORMAL (20-80%)
    2: FLUSH (Top 20%)
    """
    min_p = min(window, max(24, window // 10))
    ranks = trailing_percentile_rank(quote_volume, window=window, lag=1, min_periods=min_p)
    
    bins = [0.0, 0.2, 0.8, 1.0]
    labels = [0.0, 1.0, 2.0]
    return pd.cut(ranks, bins=bins, labels=labels, include_lowest=True).astype(float)

def calculate_ms_oi_state(oi_delta_1h: pd.Series, window: int = 288) -> pd.Series:
    """
    OI Dimension based on 1h OI delta z-score:
    0: DECEL (z < -1.5)
    1: STABLE (-1.5 <= z <= 1.5)
    2: ACCEL (z > 1.5)
    """
    min_p = min(window, max(24, window // 10))
    mean = trailing_mean(oi_delta_1h, window=window, lag=1, min_periods=min_p)
    std = trailing_std(oi_delta_1h, window=window, lag=1, min_periods=min_p)
    delta = oi_delta_1h - mean
    z = delta / std.replace(0.0, np.nan)
    z = z.mask((std == 0.0) & (delta < 0.0), -np.inf)
    z = z.mask((std == 0.0) & (delta > 0.0), np.inf)
    
    state = pd.Series(1.0, index=oi_delta_1h.index)
    state[z < -1.5] = 0.0
    state[z > 1.5] = 2.0
    # Keep NaN if inputs are NaN
    state[oi_delta_1h.isna()] = np.nan
    return state.astype(float)

def calculate_ms_funding_state(funding_rate_bps: pd.Series, window: int = 96, window_long: int = 8640, abs_floor_bps: float = 1.0) -> pd.Series:
    """
    Funding Dimension based on trailing 8h sign consistency and 30d extreme tails:
    0: NEUTRAL
    1: PERSISTENT (Same sign for 80%+ of the 8h window AND magnitude >= q65)
    2: EXTREME (Abs mean >= max(90th percentile over 30d, floor))
    """
    min_p_short = min(window, max(12, window // 8))
    # For a 30-day window, allow it to compute as long as we have at least 1 day of data
    min_p_long = min(window_long, 288) 
    
    abs_mean = trailing_mean(funding_rate_bps, window=window, lag=1, min_periods=min_p_short).abs()
    
    # Calculate the quantiles of the absolute mean over the long window
    p_ext = trailing_quantile(abs_mean, window=window_long, q=0.90, lag=1, min_periods=min_p_long)
    p_65 = trailing_quantile(abs_mean, window=window_long, q=0.65, lag=1, min_periods=min_p_long)
    
    consistency = trailing_percentile_rank(funding_rate_bps.gt(0).astype(float), window=window, lag=1, min_periods=min_p_short) 
    # Wait, sign_consistency isn't exactly percentile rank. Let's stick to a custom PIT wrapper or similar.
    # Actually, sign_consistency is (max(pos, neg) / len). 
    # Let's use a rolling apply if we have to, but ensure it's lagged.
    
    def _sign_consist(x):
        if len(x) == 0: return 0.0
        pos = np.sum(x > 0)
        neg = np.sum(x < 0)
        return float(max(pos, neg) / len(x))
        
    consistency = funding_rate_bps.rolling(window=window, min_periods=min_p_short).apply(_sign_consist, raw=True).shift(1)
    
    # 0 = NEUTRAL, 1 = PERSISTENT, 2 = EXTREME
    state = pd.Series(0.0, index=funding_rate_bps.index)
    
    # Determine masks (Dual-factor persistence)
    is_persistent = (consistency >= 0.80) & (abs_mean >= p_65)
    
    # Threshold is the max of the rolling 90th percentile or the absolute floor (e.g. 1.0 bps)
    is_extreme = abs_mean >= p_ext.clip(lower=abs_floor_bps)
    
    # Precedence: EXTREME overwrites PERSISTENT
    state[is_persistent] = 1.0
    state[is_extreme] = 2.0
    
    # Keep NaN if inputs are NaN
    state[funding_rate_bps.isna()] = np.nan
    return state.astype(float)

def calculate_ms_trend_state(trend_return: pd.Series, rv: pd.Series = None, window_long: int = 8640) -> pd.Series:
    """
    Trend Dimension based on return magnitude normalized by realized volatility:
    0: CHOP (|score| <= q70)
    1: BULL (score >= q70)
    2: BEAR (score <= q30)
    """
    state = pd.Series(0.0, index=trend_return.index)
    
    if rv is None:
        # Fallback to standard deviation of return series over the same 8h horizon
        rv = trend_return.rolling(window=96, min_periods=12).std()
        
    trend_score = trend_return / (rv + 1e-6)
    
    # Needs at least ~1 day of data, targeting 30d
    min_p_long = min(window_long, 288)
    
    q70 = trailing_quantile(trend_score, window=window_long, q=0.70, lag=1, min_periods=min_p_long)
    q30 = trailing_quantile(trend_score, window=window_long, q=0.30, lag=1, min_periods=min_p_long)
    
    # 0 = CHOP, 1 = BULL, 2 = BEAR
    is_bull = trend_score >= q70
    is_bear = trend_score <= q30
    
    state[is_bull] = 1.0
    state[is_bear] = 2.0
    
    state[trend_return.isna()] = np.nan
    return state.astype(float)

def calculate_ms_spread_state(spread_z: pd.Series) -> pd.Series:
    """
    Spread Dimension based on z-score:
    0: TIGHT (z < 0.5)
    1: WIDE (z >= 0.5)
    """
    state = pd.Series(0.0, index=spread_z.index)
    state[spread_z >= 0.5] = 1.0
    state[spread_z.isna()] = np.nan
    return state.astype(float)

def encode_context_state_code(vol: pd.Series, liq: pd.Series, oi: pd.Series, fnd: pd.Series, trend: pd.Series, spread: pd.Series) -> pd.Series:
    """
    Generate ms_context_state_code as a unique permutation.
    Format: VLOFTS (Vol, Liq, OI, Funding, Trend, Spread)
    """
    code = (
        vol.fillna(0) * 100000 +
        liq.fillna(0) * 10000 +
        oi.fillna(0) * 1000 +
        fnd.fillna(0) * 100 +
        trend.fillna(0) * 10 +
        spread.fillna(0) * 1
    )
    return code.astype(float)
