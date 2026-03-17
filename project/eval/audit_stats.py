
import numpy as np
import pandas as pd
from typing import List, Dict, Any

def permutation_test(returns: pd.Series, n_permutations: int = 1000) -> float:
    """
    Calculate the p-value of the mean return using a permutation test.
    It randomly flips the signs of the returns to create a null distribution.
    """
    arr = returns.dropna().values
    if len(arr) == 0:
        return 1.0
        
    observed_mean = np.mean(arr)
    
    null_means = []
    for _ in range(n_permutations):
        # Randomly flip signs
        signs = np.random.choice([-1, 1], size=len(arr))
        null_means.append(np.mean(arr * signs))
        
    null_means = np.array(null_means)
    
    # Two-sided p-value
    p_value = np.mean(np.abs(null_means) >= np.abs(observed_mean))
    return float(p_value)

def detect_selection_bias(p_values: List[float], n_hypotheses: int) -> Dict[str, Any]:
    """
    Check if the best p-value in a set is better than what would be 
    expected by chance given the total number of hypotheses tested.
    """
    if not p_values:
        return {"is_biased": False, "reason": "No p-values provided"}
        
    best_p = min(p_values)
    # Expected best p-value from n_hypotheses independent uniform [0,1] tests is 1/(n+1)
    expected_best_p = 1.0 / (n_hypotheses + 1)
    
    # Sidak correction for the best p-value
    # alpha_corrected = 1 - (1 - alpha_global)^(1/n)
    # If best_p > alpha_corrected, we fail to reject the global null
    
    is_biased = best_p > expected_best_p * 2.0 # Heuristic: if best is 2x expected, it's weak
    
    return {
        "best_observed_p": best_p,
        "expected_best_p": expected_best_p,
        "n_hypotheses": n_hypotheses,
        "is_suspicious": bool(best_p > expected_best_p * 5.0) # Very weak best p
    }
