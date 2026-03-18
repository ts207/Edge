import numpy as np
import pandas as pd
import pytest
from project.core.causal_primitives import trailing_quantile, trailing_percentile_rank

def test_trailing_quantile_pit():
    series = pd.Series([1, 2, 3, 4, 5, 100], name="val")
    # window=3, q=0.5 (median)
    # t=2: [1, 2, 3] -> median 2
    # t=3: [2, 3, 4] -> median 3
    # t=4: [3, 4, 5] -> median 4
    # t=5: [4, 5, 100] -> median 5
    
    # With lag=1:
    # t=3 should see value from t=2 (which is 2)
    # t=4 should see value from t=3 (which is 3)
    # t=5 should see value from t=4 (which is 4)
    # t=6 (if existed) would see 5
    
    res = trailing_quantile(series, window=3, q=0.5, lag=1)
    
    assert pd.isna(res[0])
    assert pd.isna(res[1])
    assert pd.isna(res[2])
    assert res[3] == 2.0
    assert res[4] == 3.0
    assert res[5] == 4.0

def test_trailing_percentile_rank_pit():
    series = pd.Series([1, 10, 2, 11, 3, 12, 4, 13], name="val")
    # window=2, lag=1
    # t=3: current=11. Past=[1, 10]. 11 > both. Rank=1.0
    # t=4: current=3. Past=[10, 2]. 3 > 2. Rank=0.5
    # t=5: current=12. Past=[2, 11]. 12 > both. Rank=1.0
    # t=6: current=4. Past=[11, 3]. 4 > 3. Rank=0.5
    
    res = trailing_percentile_rank(series, window=2, lag=1)
    
    assert pd.isna(res[0])
    assert pd.isna(res[1])
    assert res[2] == 0.5
    assert res[3] == 1.0
    assert res[4] == 0.5
    assert res[5] == 1.0
    assert res[6] == 0.5
