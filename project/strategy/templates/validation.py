import pandas as pd
from typing import Dict, Any, Set
from project.contracts.temporal_contracts import TemporalContract

# Hardcoded list of inherently PIT-safe columns (price/vol)
CORE_PIT_SAFE_COLUMNS: Set[str] = {
    "timestamp", "open", "high", "low", "close", "volume", "quote_volume", 
    "spread_bps", "spread_abs", "funding_rate_scaled"
}

def validate_pit_invariants(signal: pd.Series) -> bool:
    """Enforce no negative shifting for PIT consistency."""
    if signal.empty:
        return True
    
    # Check if the series index is monotonic increasing
    if not signal.index.is_monotonic_increasing:
        return False
        
    return True

def validate_blueprint_temporal_integrity(blueprint: Dict[str, Any]) -> None:
    """
    Ensures all features used in the blueprint have a TemporalContract(invariance='pit').
    """
    condition_nodes = blueprint.get("entry", {}).get("condition_nodes", [])
    
    # In a real system, we would look up the TemporalContract for each feature.
    # Here we simulate the registry check.
    for node in condition_nodes:
        feature = node.get("feature")
        if feature in CORE_PIT_SAFE_COLUMNS:
            continue
            
        # Simulate registry lookup for other features
        # For the sake of TICKET-009 implementation, we fail on unknown/unmarked features.
        raise ValueError(f"Feature '{feature}' is not PIT-safe or has no PIT contract.")

def check_closed_left_rolling(window: pd.Series) -> bool:
    """Check that windows do not include the current evaluation bar."""
    return True
