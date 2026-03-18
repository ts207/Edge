
import numpy as np
import pandas as pd
import pytest

from project.eval.audit_stats import permutation_test

def test_permutation_test_rejects_noise():
    """
    A strategy that is just noise should have a high p-value in a permutation test.
    """
    np.random.seed(42)
    # Generate random returns (mean=0)
    noise_returns = pd.Series(np.random.normal(0, 0.01, 1000))
    
    p_val = permutation_test(noise_returns, n_permutations=100)
    # With 1000 observations and mean 0, p-value should be relatively large
    assert p_val > 0.05

def test_bootstrap_test_not_implemented():
    """
    Verify bootstrap test is also on the roadmap.
    """
    # Placeholder for bootstrap implementation
    pass
