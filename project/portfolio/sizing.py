from __future__ import annotations

import logging
from typing import Dict, Any

import numpy as np
import pandas as pd

from project.engine.execution_model import estimate_transaction_cost_bps
from project.portfolio.risk_budget import calculate_portfolio_risk_multiplier, get_asset_correlation_adjustment

_LOG = logging.getLogger(__name__)


def _to_decimal_return(value: float) -> float:
    numeric = float(value)
    return numeric / 10_000.0 if abs(numeric) > 1.0 else numeric


def _resolve_volatility_adjustment(vol_regime: float, portfolio_state: Dict[str, Any]) -> float:
    """
    Convert a regime-vol input into a one-way sizing throttle.

    ``vol_regime`` may arrive either as a decimal volatility estimate (e.g. 0.25
    for 25%) or in bps-like units. We only scale down when regime volatility is
    above the configured target volatility; calmer regimes do not increase size.
    """
    observed_vol = abs(_to_decimal_return(vol_regime))
    target_vol = abs(float(portfolio_state.get("target_vol", 0.0)))
    if observed_vol <= 0.0 or target_vol <= 0.0:
        return 1.0
    return float(np.clip(target_vol / observed_vol, 0.0, 1.0))


def _resolve_net_expected_return(
    expected_return_bps: float,
    expected_cost_bps: float,
) -> tuple[float, float]:
    gross_expected_return = _to_decimal_return(expected_return_bps)
    expected_cost = abs(_to_decimal_return(expected_cost_bps))
    net_expected_return = gross_expected_return - expected_cost
    return gross_expected_return, net_expected_return


def calculate_target_notional(
    event_score: float,
    expected_return_bps: float,
    expected_adverse_bps: float,
    vol_regime: float,
    liquidity_usd: float,
    portfolio_state: Dict[str, Any],
    symbol: str,
    asset_bucket: str = "default",
    expected_cost_bps: float = 0.0,
) -> Dict[str, Any]:
    """
    Calculate target notional based on trade edge and portfolio constraints.
    """
    # 1. Base Sizing from Edge (Kelly-ish / Risk-Adjusted)
    # Convert bps-like inputs to decimal returns so the multiplier is unit invariant.
    gross_expected_return, net_expected_return = _resolve_net_expected_return(
        expected_return_bps=expected_return_bps,
        expected_cost_bps=expected_cost_bps,
    )
    expected_adverse = abs(_to_decimal_return(expected_adverse_bps))
    risk_variance = max(1e-8, expected_adverse**2)
    edge = float(event_score) * net_expected_return
    
    # Kelly-like multiplier
    confidence_multiplier = np.clip(edge / risk_variance, 0.0, 5.0)
    
    # Base position size (e.g. 0.1% of portfolio per unit of confidence)
    portfolio_value = portfolio_state.get("portfolio_value", 1000000.0)
    base_notional = portfolio_value * 0.001 * confidence_multiplier
    
    # 2. Constraints
    # Liquidity cap (max 1% of available liquidity)
    liquidity_cap = liquidity_usd * 0.01
    
    # Concentration cap (max 5% of portfolio)
    concentration_cap = portfolio_value * 0.05
    
    # Portfolio Risk Adjustment
    risk_mult = calculate_portfolio_risk_multiplier(
        gross_exposure=portfolio_state.get("gross_exposure", 0.0),
        max_gross_leverage=portfolio_state.get("max_gross_leverage", 1.0),
        target_vol=portfolio_state.get("target_vol", 0.1),
        current_vol=portfolio_state.get("current_vol", 0.1),
    )
    
    # Correlation adjustment
    corr_adj = get_asset_correlation_adjustment(
        asset_bucket=asset_bucket,
        bucket_exposures=portfolio_state.get("bucket_exposures", {}),
    )

    vol_adj = _resolve_volatility_adjustment(vol_regime, portfolio_state)
    
    # Final target
    target_notional = min(
        base_notional * risk_mult * corr_adj * vol_adj,
        liquidity_cap,
        concentration_cap,
    )
    
    return {
        "target_notional": float(target_notional),
        "confidence_multiplier": float(confidence_multiplier),
        "gross_expected_return": float(gross_expected_return),
        "net_expected_return": float(net_expected_return),
        "expected_cost": float(abs(_to_decimal_return(expected_cost_bps))),
        "liquidity_cap": float(liquidity_cap),
        "concentration_cap": float(concentration_cap),
        "risk_multiplier": float(risk_mult),
        "correlation_adjustment": float(corr_adj),
        "volatility_adjustment": float(vol_adj),
    }


def calculate_execution_aware_target_notional(
    event_score: float,
    expected_return_bps: float,
    expected_adverse_bps: float,
    vol_regime: float,
    liquidity_usd: float,
    portfolio_state: Dict[str, Any],
    symbol: str,
    market_data: Dict[str, Any],
    execution_cost_config: Dict[str, Any] | None = None,
    asset_bucket: str = "default",
) -> Dict[str, Any]:
    """
    Size a trade using expected edge net of execution costs resolved from the
    shared execution model.

    We first compute a provisional size without cost drag, then estimate
    transaction cost from current market conditions using that provisional
    turnover as the participation proxy, and finally rerun sizing on the net edge.
    """
    provisional = calculate_target_notional(
        event_score=event_score,
        expected_return_bps=expected_return_bps,
        expected_adverse_bps=expected_adverse_bps,
        vol_regime=vol_regime,
        liquidity_usd=liquidity_usd,
        portfolio_state=portfolio_state,
        symbol=symbol,
        asset_bucket=asset_bucket,
        expected_cost_bps=0.0,
    )

    turnover = float(abs(provisional["target_notional"]))
    idx = pd.Index([0])
    frame = pd.DataFrame(
        {
            "spread_bps": [float(market_data.get("spread_bps", 0.0))],
            "atr_14": [market_data.get("atr_14")],
            "close": [float(market_data.get("close", market_data.get("base_price", 1.0)) or 1.0)],
            "high": [market_data.get("high", market_data.get("close", market_data.get("base_price", 1.0)) or 1.0)],
            "low": [market_data.get("low", market_data.get("close", market_data.get("base_price", 1.0)) or 1.0)],
            "quote_volume": [market_data.get("quote_volume", liquidity_usd)],
            "depth_usd": [market_data.get("depth_usd", liquidity_usd)],
            "tob_coverage": [market_data.get("tob_coverage", 1.0)],
        },
        index=idx,
    )

    config = dict(execution_cost_config or {})
    cost_series = estimate_transaction_cost_bps(
        frame=frame,
        turnover=pd.Series([turnover], index=idx, dtype=float),
        config=config,
    )
    expected_cost_bps = float(cost_series.iloc[0]) if len(cost_series) else 0.0

    resolved = calculate_target_notional(
        event_score=event_score,
        expected_return_bps=expected_return_bps,
        expected_adverse_bps=expected_adverse_bps,
        vol_regime=vol_regime,
        liquidity_usd=liquidity_usd,
        portfolio_state=portfolio_state,
        symbol=symbol,
        asset_bucket=asset_bucket,
        expected_cost_bps=expected_cost_bps,
    )
    resolved["estimated_execution_cost_bps"] = expected_cost_bps
    resolved["provisional_target_notional"] = provisional["target_notional"]
    return resolved
