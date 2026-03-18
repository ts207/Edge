import pandas as pd
from typing import Dict, Any, Set
from project.contracts.temporal_contracts import TemporalContract

# Hardcoded list of inherently PIT-safe columns (price/vol)
CORE_PIT_SAFE_COLUMNS: Set[str] = {
    "timestamp", "open", "high", "low", "close", "volume", "quote_volume", 
    "spread_bps", "spread_abs", "funding_rate_scaled"
}

def validate_pit_invariants(signal: pd.Series) -> bool:
    """Return True iff the signal index is strictly monotone increasing.

    A non-monotone index indicates potential lookahead or unsorted data,
    both of which violate point-in-time discipline.
    """
    if signal.empty:
        return True
    return bool(signal.index.is_monotonic_increasing) and not bool(signal.index.duplicated().any())


def check_closed_left_rolling(window: pd.Series) -> bool:
    """Return True iff the rolling window index is monotone increasing.

    A properly constructed closed-left rolling window [T-N, T-1] must have
    a monotone index. A non-monotone window suggests unsorted or incorrectly
    sliced data that could include the current evaluation bar.
    """
    if window.empty:
        return True
    return bool(window.index.is_monotonic_increasing)
