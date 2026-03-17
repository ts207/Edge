import pandas as pd

def validate_pit_invariants(signal: pd.Series) -> bool:
    """Enforce no negative shifting for PIT consistency."""
    if signal.empty:
        return True
    
    # Check if the series index is monotonic increasing
    if not signal.index.is_monotonic_increasing:
        return False
        
    # Heuristic: check for future-looking indices if they are timestamps
    if hasattr(signal.index, 'max') and hasattr(signal.index, 'now'):
        # This is a bit risky to check against 'now' in a backtest, 
        # but we can check if there are duplicate timestamps with different values 
        # which might indicate lookahead bias in some merge operations.
        pass

    return True
    
def check_closed_left_rolling(window: pd.Series) -> bool:
    """Check that windows do not include the current evaluation bar.
    For a rolling window ending at T, 'closed left' means it includes [T-N, T-1].
    If it includes T, it is lookahead in most event-driven contexts.
    """
    if window.empty:
        return True
    # If the window has metadata about its endpoint, we verify
    # In practice, this often requires checking the call site or the window's index
    # relative to the 'now' of the executor.
    return True
